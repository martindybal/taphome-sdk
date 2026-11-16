"""Tests for ButtonDevice gesture handling."""

from unittest.mock import Mock

from taphome_sdk import ApiConnectionType, ButtonAction, ButtonDevice, ValueType
from taphome_sdk.device_factory import DeviceFactory
from taphome_sdk.observable import ObservableValue

from .conftest import make_metadata


def _make_button(
    initial_values: dict[ValueType, float] | None = None,
) -> tuple[ButtonDevice, list[ButtonAction]]:
    metadata = make_metadata(
        1, ValueType.BUTTON_PRESSED.value, ValueType.BUTTON_HELD_STATE.value
    )
    device = DeviceFactory.create_device(
        Mock(),
        ObservableValue(ApiConnectionType.LOCAL),
        metadata,
        initial_values or {ValueType.BUTTON_PRESSED: 0.0},
    )
    assert isinstance(device, ButtonDevice)
    clicks: list[ButtonAction] = []
    device.clicked += clicks.append
    return device, clicks


def test_long_press_fires_once_despite_held_state_updates() -> None:
    # A long press pushes ButtonPressed once, then ButtonHeldState on hold
    # start and release (taphome-homeassistant issue #211).
    device, clicks = _make_button()
    state = device.state

    state.apply_changes({ValueType.BUTTON_PRESSED: 2}, changed_only=True)
    state.apply_changes({ValueType.BUTTON_HELD_STATE: 1}, changed_only=True)
    state.apply_changes({ValueType.BUTTON_HELD_STATE: 0}, changed_only=True)

    assert clicks == [ButtonAction.LONG_PRESS]
    assert state.action is ButtonAction.NONE


def test_repeated_gesture_fires_for_each_push() -> None:
    device, clicks = _make_button()
    state = device.state

    state.apply_changes({ValueType.BUTTON_PRESSED: 2}, changed_only=True)
    state.apply_changes({ValueType.BUTTON_PRESSED: 2}, changed_only=True)

    assert clicks == [ButtonAction.LONG_PRESS, ButtonAction.LONG_PRESS]


def test_poll_snapshot_with_stale_gesture_does_not_refire() -> None:
    device, clicks = _make_button()
    state = device.state

    state.apply_changes({ValueType.BUTTON_PRESSED: 2}, changed_only=True)
    # A later poll returns a full snapshot: the stale ButtonPressed value
    # plus an unrelated change.
    state.apply_changes({ValueType.BUTTON_PRESSED: 2, ValueType.OPERATION_MODE: 1})

    assert clicks == [ButtonAction.LONG_PRESS]


def test_poll_detects_new_gesture_by_value_change() -> None:
    device, clicks = _make_button()

    device.state.apply_changes({ValueType.BUTTON_PRESSED: 3})

    assert clicks == [ButtonAction.DOUBLE_PRESS]


def test_initial_stale_gesture_does_not_fire() -> None:
    device, clicks = _make_button({ValueType.BUTTON_PRESSED: 2.0})

    assert clicks == []
    assert device.state.action is None


def test_empty_push_delta_is_ignored() -> None:
    # A webhook carrying only value types unknown to the SDK parses to an
    # empty delta and must not touch the state.
    device, clicks = _make_button()
    state = device.state

    state.apply_changes({ValueType.BUTTON_PRESSED: 2}, changed_only=True)
    state.apply_changes({}, changed_only=True)

    assert clicks == [ButtonAction.LONG_PRESS]
