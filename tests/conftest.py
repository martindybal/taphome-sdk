"""Shared fixtures and helpers for taphome-sdk tests."""

from unittest.mock import Mock

import pytest

from taphome_sdk import ApiConnectionType
from taphome_sdk.observable import ObservableValue
from taphome_sdk.taphome_api import DeviceMetadata


@pytest.fixture
def connection_type() -> ObservableValue[ApiConnectionType]:
    return ObservableValue(ApiConnectionType.LOCAL)


@pytest.fixture
def api() -> Mock:
    return Mock()


def make_metadata(device_id: int, *value_type_ids: int, **overrides) -> DeviceMetadata:
    """Build DeviceMetadata from raw API-shaped data."""
    data = {
        "deviceId": device_id,
        "type": overrides.get("type", "TestDevice"),
        "name": overrides.get("name", f"Device {device_id}"),
        "description": overrides.get("description", f"Description {device_id}"),
        "supportedValues": [
            {"valueTypeId": type_id, "readOnly": False} for type_id in value_type_ids
        ],
    }
    return DeviceMetadata.from_dict(data)
