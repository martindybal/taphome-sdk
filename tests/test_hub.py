"""Tests for TapHomeHub webhook handling and device lookup."""

from unittest.mock import Mock

import pytest

from taphome_sdk import (
    ApiConnectionType,
    ButtonAction,
    ButtonDevice,
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


async def test_webhook_fires_button_gesture_per_push() -> None:
    # The webhook is a changed-values delta: pushing the same gesture twice
    # must fire twice even though the cached value does not change.
    hub = TapHomeHub("http://hub.local/api", "token", Mock())
    metadata = make_metadata(2, ValueType.BUTTON_PRESSED.value)
    device = DeviceFactory.create_device(
        Mock(), hub.connection_type, metadata, {ValueType.BUTTON_PRESSED: 0.0}
    )
    assert isinstance(device, ButtonDevice)
    hub.devices[2] = device
    hub.connection_state.value = HubConnectionState.CONNECTED
    clicks: list[ButtonAction] = []
    device.clicked += clicks.append

    payload = {
        "devices": [
            {
                "deviceId": 2,
                "values": [{"valueTypeId": ValueType.BUTTON_PRESSED.value, "value": 2}],
            }
        ],
        "timestamp": 2,
    }
    await hub.async_handle_webhook(payload)
    await hub.async_handle_webhook(payload | {"timestamp": 3})

    assert clicks == [ButtonAction.LONG_PRESS, ButtonAction.LONG_PRESS]


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
