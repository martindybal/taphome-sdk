# Changelog

## 1.0.0

First release of the rewritten SDK, extracted from the
[TapHome Home Assistant integration](https://github.com/martindybal/taphome-homeassistant)
(previously bundled there as `taphome_sdk`). Replaces the legacy cloud-only
SDK that lived in the `python/` folder of this repository.

Changes against the bundled version:

- `TapHomeApi`, `TapHomeHub` and `TapHomeHubFactory.async_connect` now take an
  `aiohttp.ClientSession` owned by the caller; the SDK no longer creates a
  session per request.
- New `exceptions` module: `TapHomeError`, `TapHomeAuthError`,
  `TapHomeConnectionError`. Network and HTTP errors raise
  `TapHomeConnectionError` instead of `aiohttp` exceptions or `ValueError`.
- `TapHomeHub.async_handle_webhook` takes the parsed JSON payload (`dict`)
  instead of an `aiohttp.web.Request`, removing the dependency on the aiohttp
  server side.
- The package ships type information (`py.typed`).
