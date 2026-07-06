"""Tests for Event and ObservableValue."""

from taphome_sdk.observable import Event, ObservableValue


def test_event_notifies_subscribers() -> None:
    event: Event = Event()
    calls: list[tuple] = []
    event.subscribe(lambda *args: calls.append(args))

    event(1, 2)

    assert calls == [(1, 2)]


def test_event_replays_last_value_to_new_subscriber() -> None:
    event: Event = Event()
    event("old", "new")

    calls: list[tuple] = []
    event.subscribe(lambda *args: calls.append(args))

    assert calls == [("old", "new")]


def test_event_unsubscribe_stops_notifications() -> None:
    event: Event = Event()
    calls: list[tuple] = []

    def handler(*args) -> None:
        calls.append(args)

    event += handler
    event(1)
    event -= handler
    event(2)

    assert calls == [(1,)]


def test_observable_value_notifies_on_change() -> None:
    observable = ObservableValue(1)
    changes: list[tuple[int, int]] = []
    observable.changed.subscribe(lambda old, new: changes.append((old, new)))

    observable.value = 2

    assert observable.value == 2
    assert changes[-1] == (1, 2)


def test_observable_value_skips_notification_when_unchanged() -> None:
    observable = ObservableValue(1)
    changes: list[tuple[int, int]] = []
    observable.changed.subscribe(lambda old, new: changes.append((old, new)))
    changes.clear()

    observable.value = 1

    assert changes == []
