# taphome-sdk

Async Python client for the [TapHome](https://taphome.com) smart home
[API](https://taphome.com/en/support/601227274). Originally developed for the
[TapHome Home Assistant integration](https://github.com/martindybal/taphome-homeassistant),
usable from any asyncio application.

## Installation

```bash
pip install taphome-sdk
```

## Usage

```python
import asyncio

import aiohttp

from taphome_sdk import TapHomeHubFactory


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        hub = await TapHomeHubFactory.async_connect(
            "http://192.168.1.10/api/TapHomeApi/v1",  # or https://api.taphome.com/api/TapHomeApi/v1
            "your-api-token",
            session,
        )
        try:
            for device in hub.devices.values():
                print(device.id, device.name, type(device).__name__)
        finally:
            hub.disconnect()


asyncio.run(main())
```

Key concepts:

- **`TapHomeHubFactory.async_connect(api_url, token, session)`** discovers all
  devices exposed in the TapHome API and returns a connected `TapHomeHub`.
  Raises `TapHomeAuthError` for a rejected token and `TapHomeConnectionError`
  when the hub cannot be reached. The `aiohttp.ClientSession` is owned by the
  caller and never closed by the SDK.
- **`hub.devices`** maps device ids to typed devices (`RGBLightDevice`,
  `ThermostatDevice`, `BidirectionalDevice`, …) created by `DeviceFactory`
  from the value types each device supports.
- **`device.state`** is an `ObservableValue`; subscribe to `state.changed` to
  get push updates. The hub also polls periodically as a fallback.
- **`hub.async_handle_webhook(payload)`** feeds a parsed webhook JSON body
  into the hub for instant push updates.
- **`hub.disconnect()`** stops the periodic refresh task.

## Development

```bash
pip install -e . pytest pytest-asyncio ruff mypy
pytest
ruff check .
mypy
```

## Releasing

1. Bump `version` in `pyproject.toml` and update `CHANGELOG.md`.
2. Create a GitHub release with tag `v<version>` (e.g. `v1.0.0`).
3. The `Release to PyPI` workflow builds and publishes the package via
   [trusted publishing](https://docs.pypi.org/trusted-publishers/) — no API
   tokens are stored in the repository.

## License

[GPL-3.0-or-later](LICENSE).
