import asyncio

import httpx
from fastapi import HTTPException

import ollama_api


class _FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_ollama_request_maps_upstream_5xx_to_502(monkeypatch):
    class _Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return _FakeResponse(500, {"error": "internal"})

        async def request(self, method, url, json):
            return _FakeResponse(500, {"error": "internal"})

    monkeypatch.setattr(ollama_api.httpx, "AsyncClient", _Client)

    try:
        asyncio.run(ollama_api.ollama_request("GET", "/api/tags"))
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 502
        assert exc.detail == "internal"


def test_ollama_request_maps_upstream_4xx_to_400(monkeypatch):
    class _Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return _FakeResponse(404, {"error": "not found"})

        async def request(self, method, url, json):
            return _FakeResponse(404, {"error": "not found"})

    monkeypatch.setattr(ollama_api.httpx, "AsyncClient", _Client)

    try:
        asyncio.run(ollama_api.ollama_request("GET", "/api/tags"))
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "not found"


def test_ollama_request_connection_error_is_502(monkeypatch):
    class _Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            raise httpx.ConnectError("down")

        async def request(self, method, url, json):
            raise httpx.ConnectError("down")

    monkeypatch.setattr(ollama_api.httpx, "AsyncClient", _Client)

    try:
        asyncio.run(ollama_api.ollama_request("GET", "/api/tags"))
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 502
        assert "Cannot reach Ollama" in exc.detail
