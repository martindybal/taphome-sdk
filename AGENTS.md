# AGENTS.md

Guidance for coding agents (Claude Code, Codex, …) working in this repository.

## What this repository is

`taphome-sdk` — an async Python client for the [TapHome](https://taphome.com)
smart home API, published to PyPI. No Home Assistant imports; the only runtime
dependency is `aiohttp`. Python `>=3.12`, license GPL-3.0-or-later, semver
versioning in `pyproject.toml`.

The primary consumer is the
[taphome-homeassistant](https://github.com/martindybal/taphome-homeassistant)
integration (usually checked out as a sibling directory; its `sdk_locator.py`
prefers this checkout's `src/` during development). The integration pins an
**exact** SDK version in its `manifest.json`, so API changes here must ship as
a PyPI release before the integration can use them, and breaking changes need
a coordinated bump on both sides.

## Commands

```bash
pip install -e . pytest pytest-asyncio ruff mypy

pytest tests -q        # unit tests (asyncio_mode=auto)
ruff check .           # lint (config in pyproject.toml)
mypy                   # strict typing — `strict = true`, packages=taphome_sdk
```

Pitfalls:

- Run mypy **from this directory** (config uses `packages`/`mypy_path`), never
  from the integration repo — its root-level `select.py`/`time.py` shadow the
  stdlib and break tool startup.
- `tests/test_http_client.py` starts a real local aiohttp server. Run the
  suite in an environment **without** `pytest-homeassistant-custom-component`
  installed — its pytest plugin blocks sockets globally and produces six false
  failures.

## Architecture

Everything lives in `src/taphome_sdk/`:

- `taphome_api.py` — `TapHomeApi`, the raw HTTP client (local
  `http://<ip>/api/TapHomeApi/v1` or cloud `https://api.taphome.com/...`),
  response dataclasses (`DiscoveryResponse`, `DevicesValuesResponse`,
  `SetDeviceValueResponse`, …) built via `from_dict`, and the internal
  `_TapHomeHttpClient`. The aiohttp `ClientSession` is **owned by the caller**
  and must never be closed here.
- `exceptions.py` — `TapHomeError` is the base of **every** SDK error:
  `TapHomeAuthError` (HTTP 401/403), `TapHomeConnectionError`,
  `ValueChangeFailedException` (Core rejected a change or returned no usable
  response), `DeviceNotExposedError`, `DeviceTypeError` (the last three are
  defined next to their raisers but keep the common base). Failures are
  raised, never silently logged-and-swallowed.
- `observable.py` — `Event` (C#-style, subscribe with `+=`; **replays the last
  value to new subscribers**) and `ObservableValue` (fires `changed(old, new)`
  only when the value actually changes).
- `device.py` + `device_*.py` — typed device classes, each with an observable
  `state`. `DeviceFactory.create_device` picks the class by which `ValueType`s
  the device supports, checked in priority order (e.g. `BLINDS_LEVEL` →
  `BidirectionalDevice`, `TEMPERATURE_SET_POINT` → `ThermostatDevice`);
  a fallthrough returns the plain `Device`. Writes go through
  `Device.async_set_device_values`, which verifies the Core's response and
  reloads values afterwards (except on LOCAL_PUSH connections).
- `taphome_hub.py` — `TapHomeHub`: device registry (`devices: dict[int,
  Device]`), `connection_state` (`CONNECTED`/`FAILED`/`AUTH_FAILED`/
  `DISCONNECTED`), and the refresh loop. Poll interval by `ApiConnectionType`:
  LOCAL 2 s, CLOUD 20 s, LOCAL_PUSH 60 s (a webhook payload switches the type
  to LOCAL_PUSH). Poll failures log one warning, then debug until recovery;
  an auth failure sets `AUTH_FAILED` instead of `FAILED` so callers can
  re-authenticate. `async_discover_new_devices()` re-runs discovery at runtime
  and registers newly exposed devices (existing ones are kept even if they
  disappear from the API). `get_typed_device(id, *types)` is the typed lookup
  used by consumers.
- `helpers.py` — enum-from-string helpers, `FromDictProtocol`,
  `set_interval_async`.

Public API is whatever `__init__.py` re-exports — new names consumers need
must be added there.

## Conventions

- `mypy --strict` must stay clean; the package ships `py.typed`.
- Ruff rules include `D` (docstrings) — every public module/class/function is
  documented; tests are exempt.
- Every release: bump `version` in `pyproject.toml` (semver) and add a
  `CHANGELOG.md` section describing user-visible changes; then update the
  pinned version in the integration's `manifest.json`.
- Keep this package free of Home Assistant concepts — HA-specific behavior
  belongs in the integration.
