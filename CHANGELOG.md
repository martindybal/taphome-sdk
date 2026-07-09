# Changelog

## 1.1.0

- `ValueChangeFailedException` is exported from the package root, inherits
  from `TapHomeError` and carries `device_id` and `values` attributes.
- `Device.async_set_device_values` raises `ValueChangeFailedException` when
  the API returns no usable response instead of silently logging an error.
- `DeviceNotExposedError` and `DeviceTypeError` inherit from `TapHomeError`.
- New `HubConnectionState.AUTH_FAILED`: the hub reports a rejected token
  separately from an unreachable core, so callers can start a re-auth.
- New `TapHomeHub.async_discover_new_devices()` re-runs discovery at runtime
  and registers devices exposed after the initial connect.
- New `TapHomeHub.new_device_ids` observable: ids seen in incoming values
  (webhook or poll) that are not registered devices yet, so callers can react
  to a newly exposed device instead of polling discovery on a timer.
- Repeated poll failures are logged once at warning level and then at debug
  until the connection recovers, instead of one error per poll cycle.
- The package now type-checks under `mypy --strict`.

## 1.0.0

First release of the SDK, extracted from the
[TapHome Home Assistant integration](https://github.com/martindybal/taphome-homeassistant)
(previously bundled there as `taphome_sdk`).
