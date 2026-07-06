"""Tests for TapHomeHub webhook handling and device lookup."""

from unittest.mock import Mock

import pytest

from taphome_sdk import (
    ApiConnectionType,
    DeviceNotExposedError,
    DeviceTypeError,
    DigitalOutputDevice,
    HubConnectionState,
    TapHomeHub,
    ValueType,
    VariableDevice,
)
from taphome_sdk.device_factory import DeviceFactory

from .conftest import make_metadata


def _make_hub_with_switch() -> tuple[TapHomeHub, DigitalOutputDevice]:
    hub = TapHomeHub("http://hub.local/api", "token", Mock())
    metadata = make_metadata(1, ValueType.SWITCH_STATE.value)
    device = DeviceFactory.create_device(
        Mock(), hub.connection_type, metadata, {ValueType.SWITCH_STATE: 0.0}
    )
    assert isinstance(device, DigitalOutputDevice)
    hub.devices[1] = device
    hub.connection_state.value = HubConnectionState.CONNECTED
    return hub, device


async def test_webhook_payload_updates_device_state() -> None:
    hub, device = _make_hub_with_switch()
    assert device.state.is_on is False

    await hub.async_handle_webhook(
        {
            "devices": [
                {
                    "deviceId": 1,
                    "values": [
                        {"valueTypeId": ValueType.SWITCH_STATE.value, "value": 1}
                    ],
                }
            ],
            "timestamp": 2,
        }
    )

    assert device.state.is_on is True
    assert hub.connection_type.value is ApiConnectionType.LOCAL_PUSH


def test_get_typed_device_checks_type() -> None:
    hub, device = _make_hub_with_switch()

    assert hub.get_typed_device(1, DigitalOutputDevice) is device

    with pytest.raises(DeviceNotExposedError):
        hub.get_typed_device(2, DigitalOutputDevice)

    with pytest.raises(DeviceTypeError):
        hub.get_typed_device(1, VariableDevice)


def test_disconnect_is_idempotent() -> None:
    hub, _ = _make_hub_with_switch()
    hub.disconnect()
    hub.disconnect()
    assert hub.connection_state.value is HubConnectionState.DISCONNECTED
