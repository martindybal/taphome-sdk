"""Tests for the API response models."""

from taphome_sdk import ValueType
from taphome_sdk.taphome_api import (
    DeviceMetadata,
    DevicesValuesResponse,
    Location,
    SetDeviceValueResponse,
    ValueChangeResult,
)


def test_device_metadata_from_dict() -> None:
    metadata = DeviceMetadata.from_dict(
        {
            "deviceId": 7,
            "type": "Light",
            "usage": "light",
            "name": "Kitchen light",
            "description": "Main kitchen light",
            "zone": "Kitchen",
            "category": "Lights",
            "supportedValues": [
                {"valueTypeId": ValueType.SWITCH_STATE.value, "readOnly": False},
                {"valueTypeId": 99999, "readOnly": False},  # unknown -> skipped
            ],
        }
    )

    assert metadata.id == 7
    assert metadata.device_type == "Light"
    assert metadata.zone == "Kitchen"
    assert metadata.supports_value(ValueType.SWITCH_STATE)
    assert not metadata.supports_value(ValueType.BLINDS_LEVEL)


def test_location_from_dict() -> None:
    location = Location.from_dict(
        {
            "locationId": "abc-123",
            "locationName": "Test Home",
            "tapHomeApiVersion": 1,
            "timestamp": 42,
        }
    )

    assert location.location_id == "abc-123"
    assert location.location_name == "Test Home"


def test_devices_values_response_skips_unknown_value_types() -> None:
    response = DevicesValuesResponse.from_dict(
        {
            "devices": [
                {
                    "deviceId": 1,
                    "values": [
                        {"valueTypeId": ValueType.SWITCH_STATE.value, "value": 1},
                        {"valueTypeId": 99999, "value": 5},
                    ],
                }
            ],
            "timestamp": 1,
        }
    )

    assert response.devices[1].values == {ValueType.SWITCH_STATE: 1}


def test_set_device_value_response_maps_results() -> None:
    response = SetDeviceValueResponse.from_dict(
        {
            "deviceId": 3,
            "valuesChanged": [
                {"typeId": ValueType.SWITCH_STATE.value, "result": "CHANGED"},
            ],
            "timestamp": 1,
        }
    )

    assert response.values_changed == {
        ValueType.SWITCH_STATE: ValueChangeResult.CHANGED
    }


def test_value_change_result_from_string() -> None:
    assert ValueChangeResult.from_string("changed") is ValueChangeResult.CHANGED
    assert ValueChangeResult.from_string("NOTCHANGED") is ValueChangeResult.NOT_CHANGED
    assert ValueChangeResult.from_string("failed") is ValueChangeResult.FAILED
    assert ValueChangeResult.from_string("garbage") is ValueChangeResult.FAILED
