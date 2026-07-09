"""TapHome Hub handles communication with TapHome Core."""

from asyncio import Task
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from enum import Enum
import logging
from typing import Any, NoReturn, TypeVar, cast

from aiohttp import ClientSession

from .device import Device
from .device_analog_output import AnalogOutputDevice
from .device_bidirectional import BidirectionalDevice
from .device_digital_output import DigitalOutputDevice
from .device_factory import DeviceFactory
from .device_generic_output_adapter import OutputCapableDevice
from .exceptions import TapHomeAuthError, TapHomeConnectionError, TapHomeError
from .helpers import set_interval_async
from .observable import ObservableValue
from .taphome_api import (
    ApiConnectionType,
    DevicesValuesResponse,
    DeviceValues,
    Location,
    TapHomeApi,
)

_LOGGER = logging.getLogger(__name__)


class HubConnectionState(Enum):
    """Enum representing the hub connection state."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    FAILED = "failed"
    AUTH_FAILED = "auth_failed"


DeviceT = TypeVar("DeviceT", bound=Device[Any])


class DeviceNotExposedError(TapHomeError):
    """Device is not exposed to TapHome API."""

    def __init__(self, device_id: int) -> None:
        """Initialize the exception with the device ID."""
        self.device_id = device_id
        super().__init__(
            f"Device with ID {device_id} has not been exposed in the TapHome API"
        )


class DeviceTypeError(TapHomeError):
    """Unexpected device type returned for a TapHome device."""

    def __init__(
        self,
        device_id: int,
        device_class_name: str,
        device_type: str,
        supported_values: str,
        expected_device_types: str,
    ) -> None:
        """Initialize the exception with the device ID and types."""
        msg = (
            f"Device with ID {device_id} is type {device_class_name} "
            f"(device_type={device_type}, "
            f"supported_values=[{supported_values}]) not one of: {expected_device_types}"
        )
        super().__init__(msg)
        self.device_id = device_id
        self.device_type = device_type
        self.supported_values = supported_values
        self.expected_device_types = expected_device_types


class TapHomeHub:
    """TapHome Hub connection class."""

    location: Location | None = None
    last_update_success_time: ObservableValue[datetime | None]
    connection_type: ObservableValue[ApiConnectionType]
    connection_state: ObservableValue[HubConnectionState]
    # Device ids seen in incoming values (webhook or poll) that are not yet
    # registered. Exposing a device in the TapHome app makes it show up here,
    # so callers can react instead of polling discovery on a timer.
    new_device_ids: ObservableValue[frozenset[int]]

    def __init__(
        self,
        api_url: str,
        token: str,
        session: ClientSession,
    ) -> None:
        """Initialize the TapHome Hub with an API instance.

        ``session`` is owned by the caller and is never closed by the SDK.
        """
        self.api = TapHomeApi(api_url, token, session)
        self.last_update_success_time = ObservableValue(None)
        self.connection_state = ObservableValue(HubConnectionState.DISCONNECTED)
        connection_type = (
            ApiConnectionType.CLOUD
            if "taphome.com" in api_url
            else ApiConnectionType.LOCAL
        )
        self.connection_type = ObservableValue(connection_type)

        self.new_device_ids = ObservableValue(frozenset[int]())
        self.devices: dict[int, Device[Any]] = {}
        self.periodic_refresh_task: Task[None] | None = None
        self._connection_type_changed_handler = lambda _, __: (
            self._schedule_periodic_refresh()
        )

    def get_generic_output_capable_device(self, device_id: int) -> OutputCapableDevice:
        """Get a digital output device by its ID."""
        device = self.get_typed_device(
            device_id,
            DigitalOutputDevice,
            AnalogOutputDevice,
            BidirectionalDevice,
        )

        return cast(OutputCapableDevice, device)

    def get_typed_device(self, device_id: int, *device_types: type[DeviceT]) -> DeviceT:
        """Get a device by its ID and ensure it is of the specified type(s)."""
        device = self.devices.get(device_id)

        if device is None:
            raise DeviceNotExposedError(device_id)

        if not isinstance(device, device_types):
            device_class_name = device.__class__.__name__
            expected_device_types = ", ".join(t.__name__ for t in device_types)
            supported_values = ", ".join(
                value_type.name for value_type in device.supported_values
            )
            raise DeviceTypeError(
                device_id,
                device_class_name,
                device.device_type,
                supported_values,
                expected_device_types,
            )

        return device

    async def async_connect(self) -> None:
        """Connect to the TapHome API."""
        try:
            self.location = await self.api.async_get_location()
            discovery = await self.api.async_discovery_devices()
            values = await self.api.async_get_all_devices_values()

            if self.location is None or discovery is None or values is None:
                self._empty_response()

            for metadata in discovery.devices.values():
                device_values = values.devices[metadata.id]
                device = DeviceFactory.create_device(
                    self.api, self.connection_type, metadata, device_values.values
                )
                if device is not None:
                    self.devices[metadata.id] = device

            self._schedule_periodic_refresh()
            self.connection_type.changed += self._connection_type_changed_handler
            self.connection_state.value = HubConnectionState.CONNECTED

        except Exception as e:
            _LOGGER.error("Failed to connect to TapHome API: %s", e)
            raise

    async def async_discover_new_devices(self) -> set[int]:
        """Re-run discovery and register devices exposed since the connect.

        Returns the ids of every device the API currently exposes. Devices
        that disappeared from the API are kept in ``devices`` so existing
        references stay valid.
        """
        discovery = await self.api.async_discovery_devices()
        if discovery is None:
            self._empty_response()

        new_ids = set(discovery.devices) - set(self.devices)
        if new_ids:
            values = await self.api.async_get_all_devices_values()
            if values is None:
                self._empty_response()
            for device_id in new_ids:
                device_values = values.devices.get(device_id)
                device = DeviceFactory.create_device(
                    self.api,
                    self.connection_type,
                    discovery.devices[device_id],
                    device_values.values if device_values is not None else {},
                )
                if device is not None:
                    self.devices[device_id] = device

        # Drop ids that are now registered; anything left is still unknown and
        # will re-fire so the caller can try again.
        self.new_device_ids.value = self.new_device_ids.value - self.devices.keys()
        return set(discovery.devices)

    def disconnect(self) -> None:
        """Stop periodic polling and mark the hub as disconnected."""
        self.connection_type.changed -= self._connection_type_changed_handler
        if self.periodic_refresh_task is not None:
            self.periodic_refresh_task.cancel()
            self.periodic_refresh_task = None
        self.connection_state.value = HubConnectionState.DISCONNECTED

    async def async_handle_webhook(self, payload: dict[str, Any]) -> None:
        """Handle an incoming webhook payload (parsed JSON body)."""
        self.connection_type.value = ApiConnectionType.LOCAL_PUSH
        if self.connection_state.value == HubConnectionState.CONNECTED:
            changed_values = DevicesValuesResponse.from_dict(payload)
            self._update_devices_values(changed_values.devices)
        else:
            await self._async_update_all_devices_values()

    def _schedule_periodic_refresh(self) -> None:
        if self.periodic_refresh_task is not None:
            self.periodic_refresh_task.cancel()

        self.periodic_refresh_task = set_interval_async(
            self._async_update_all_devices_values, self._update_interval
        )

    @property
    def _update_interval(self) -> timedelta:
        if self.connection_type.value == ApiConnectionType.LOCAL_PUSH:
            return timedelta(seconds=60)
        if self.connection_type.value == ApiConnectionType.LOCAL:
            return timedelta(seconds=2)
        return timedelta(seconds=20)

    async def _async_update_all_devices_values(
        self,
    ) -> None:
        try:
            values = await self.api.async_get_all_devices_values()
            if values is None:
                self._empty_response()

            self._update_devices_values(values.devices)
            self.connection_state.value = HubConnectionState.CONNECTED
        except TapHomeAuthError as error:
            if self.connection_state.value is not HubConnectionState.AUTH_FAILED:
                _LOGGER.warning("TapHome API rejected the token: %s", error)
            self.connection_state.value = HubConnectionState.AUTH_FAILED
        except Exception:
            # Log the first failure loudly; while the hub stays unreachable
            # every further poll failure is only interesting for debugging.
            if self.connection_state.value is HubConnectionState.CONNECTED:
                _LOGGER.warning(
                    "Failed to update TapHome data. Last successful update: %s",
                    self.last_update_success_time.value,
                    exc_info=True,
                )
            else:
                _LOGGER.debug(
                    "TapHome update keeps failing. Last successful update: %s",
                    self.last_update_success_time.value,
                    exc_info=True,
                )
            self.connection_state.value = HubConnectionState.FAILED

    def _empty_response(self) -> NoReturn:
        raise TapHomeConnectionError(
            "Empty response from TapHome API. "
            "This may indicate a network issue, invalid API credentials, "
            "or a problem with the TapHome server. "
            "Please check your connection and try again."
        )

    def _update_devices_values(self, values: dict[int, DeviceValues]) -> None:
        for device_id, device_values in values.items():
            device = self.devices.get(device_id)
            if device is not None and device_values is not None:
                device.state.apply_changes(device_values.values)

        self.last_update_success_time.value = datetime.now(UTC)
        self._track_new_device_ids(values.keys())

    def _track_new_device_ids(self, seen_ids: Iterable[int]) -> None:
        """Record ids seen in the values that are not registered devices.

        Accumulates across calls (a webhook carries only changed devices) and
        drops ids once their device is registered, so the value only grows when
        a genuinely new device appears.
        """
        known = self.devices.keys()
        tracked = (self.new_device_ids.value | set(seen_ids)) - known
        self.new_device_ids.value = frozenset(tracked)


class TapHomeHubFactory:
    """Factory for creating TapHome hub connections."""

    @staticmethod
    async def async_connect(
        api_url: str, token: str, session: ClientSession
    ) -> TapHomeHub:
        """Connect to TapHome and return an instance of TapHomeHub."""
        hub = TapHomeHub(api_url, token, session)

        if hub.connection_type.value == ApiConnectionType.CLOUD:
            _LOGGER.warning(
                "Connecting to TapHome Cloud API. "
                "This may be slow and is not recommended for production use"
            )
        await hub.async_connect()
        return hub
