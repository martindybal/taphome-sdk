"""Tests for the HTTP layer: session injection and error mapping."""

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

from taphome_sdk import TapHomeApi, TapHomeAuthError, TapHomeConnectionError


async def _make_api(handler) -> tuple[TapHomeApi, TestClient]:
    app = web.Application()
    app.router.add_get("/api/location", handler)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    api = TapHomeApi(str(client.make_url("/api")), "test-token", client.session)
    return api, client


async def test_get_location_success() -> None:
    received_headers = {}

    async def handler(request: web.Request) -> web.Response:
        received_headers.update(request.headers)
        return web.json_response(
            {
                "locationId": "loc-1",
                "locationName": "Test",
                "tapHomeApiVersion": 1,
                "timestamp": 1,
            }
        )

    api, client = await _make_api(handler)
    try:
        location = await api.async_get_location()
    finally:
        await client.close()

    assert location is not None
    assert location.location_id == "loc-1"
    assert received_headers["Authorization"] == "TapHome test-token"


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_error(status: int) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=status)

    api, client = await _make_api(handler)
    try:
        with pytest.raises(TapHomeAuthError) as error:
            await api.async_get_location()
        assert error.value.status == status
    finally:
        await client.close()


async def test_server_error_raises_connection_error() -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=500)

    api, client = await _make_api(handler)
    try:
        with pytest.raises(TapHomeConnectionError):
            await api.async_get_location()
    finally:
        await client.close()


async def test_unreachable_host_raises_connection_error() -> None:
    async with aiohttp.ClientSession() as session:
        api = TapHomeApi("http://127.0.0.1:1/api", "token", session)
        with pytest.raises(TapHomeConnectionError):
            await api.async_get_location()


async def test_invalid_json_returns_none() -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"unexpected": "shape"})

    api, client = await _make_api(handler)
    try:
        assert await api.async_get_location() is None
    finally:
        await client.close()
