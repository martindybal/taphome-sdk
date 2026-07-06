"""Tests for DeviceFactory device classification."""

import pytest

from taphome_sdk import (
    AnalogOutputDevice,
    BidirectionalDevice,
    ButtonDevice,
    Device,
    DigitalOutputDevice,
    DualWhiteLightDevice,
    MultiValueSwitchDevice,
    RGBLightDevice,
    SessionDurationVariableDevice,
    ThermostatDevice,
    ValueType,
    VariableDevice,
)
from taphome_sdk.device_factory import DeviceFactory

from .conftest import make_metadata


@pytest.mark.parametrize(
    ("value_types", "expected_type"),
    [
        ([ValueType.BLINDS_LEVEL, ValueType.BLINDS_IS_MOVING], BidirectionalDevice),
        ([ValueType.TEMPERATURE_SET_POINT], ThermostatDevice),
        (
            [ValueType.ANALOG_OUTPUT_VALUE, ValueType.ANALOG_OUTPUT_DESIRED_VALUE],
            AnalogOutputDevice,
        ),
        (
            [ValueType.HUE_BRIGHTNESS, ValueType.HUE_DEGREES, ValueType.SATURATION],
            RGBLightDevice,
        ),
        (
            [ValueType.HUE_BRIGHTNESS, ValueType.CORRELATED_COLOR_TEMPERATURE],
            DualWhiteLightDevice,
        ),
        (
            [
                ValueType.MULTI_VALUE_SWITCH_STATE,
                ValueType.MULTI_VALUE_SWITCH_DESIRED_STATE,
            ],
            MultiValueSwitchDevice,
        ),
        ([ValueType.SWITCH_STATE], DigitalOutputDevice),
        (
            [ValueType.VARIABLE_STATE, ValueType.SESSION_DURATION],
            SessionDurationVariableDevice,
        ),
        ([ValueType.VARIABLE_STATE], VariableDevice),
        ([ValueType.BUTTON_PRESSED], ButtonDevice),
        ([ValueType.HUMIDITY], Device),  # no specific match -> generic device
    ],
)
def test_create_device_classification(
    api, connection_type, value_types, expected_type
) -> None:
    metadata = make_metadata(1, *(vt.value for vt in value_types))
    values = dict.fromkeys(value_types, 0.0)

    device = DeviceFactory.create_device(api, connection_type, metadata, values)

    assert type(device) is expected_type
