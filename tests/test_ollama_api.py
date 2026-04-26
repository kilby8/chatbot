from fastapi import HTTPException
from fastapi.testclient import TestClient

import ollama_api


client = TestClient(ollama_api.app)


def test_cors_wildcard_disables_credentials():
    cors_middleware = next(
        m for m in ollama_api.app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    assert cors_middleware.kwargs["allow_origins"] == ["*"]
    assert cors_middleware.kwargs["allow_credentials"] is False


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "ollama_base_url" in body


def test_chat_happy_path(monkeypatch):
    async def fake_ollama_request(method, path, payload=None):
        assert method == "POST"
        assert path == "/api/chat"
        assert payload["model"] == "llama3.1:8b"
        return {"message": {"role": "assistant", "content": "hello"}}

    monkeypatch.setattr(ollama_api, "ollama_request", fake_ollama_request)

    response = client.post(
        "/chat",
        json={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "model": "llama3.1:8b",
        "message": {"role": "assistant", "content": "hello"},
    }


def test_chat_validation_rejects_bad_role():
    response = client.post(
        "/chat",
        json={
            "model": "llama3.1:8b",
            "messages": [{"role": "tool", "content": "hi"}],
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 422


def test_chat_validation_rejects_oversized_single_message():
    response = client.post(
        "/chat",
        json={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "x" * 8001}],
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 422


def test_chat_validation_rejects_too_many_messages():
    response = client.post(
        "/chat",
        json={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "hi"} for _ in range(101)],
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 422


def test_chat_validation_rejects_total_payload_too_large():
    messages = [{"role": "user", "content": "x" * 8000} for _ in range(7)]

    response = client.post(
        "/chat",
        json={
            "model": "llama3.1:8b",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


def test_models_endpoint(monkeypatch):
    async def fake_ollama_request(method, path, payload=None):
        assert method == "GET"
        assert path == "/api/tags"
        return {"models": [{"name": "llama3.1:8b"}]}

    monkeypatch.setattr(ollama_api, "ollama_request", fake_ollama_request)

    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == {"models": [{"name": "llama3.1:8b"}]}


def test_models_requires_api_key_when_configured(monkeypatch):
    async def fake_ollama_request(method, path, payload=None):
        assert method == "GET"
        assert path == "/api/tags"
        return {"models": [{"name": "llama3.1:8b"}]}

    monkeypatch.setattr(ollama_api, "API_AUTH_TOKEN", "secret")
    monkeypatch.setattr(ollama_api, "ollama_request", fake_ollama_request)

    unauthorized = client.get("/models")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["detail"] == "Unauthorized"

    authorized = client.get("/models", headers={"X-API-Key": "secret"})
    assert authorized.status_code == 200
    assert authorized.json() == {"models": [{"name": "llama3.1:8b"}]}


def test_chat_surfaces_upstream_errors(monkeypatch):
    async def fake_ollama_request(method, path, payload=None):
        raise HTTPException(status_code=502, detail="Ollama unavailable")

    monkeypatch.setattr(ollama_api, "ollama_request", fake_ollama_request)

    response = client.post(
        "/chat",
        json={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.7,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Ollama unavailable"


def test_chat_requires_api_key_when_configured(monkeypatch):
    async def fake_ollama_request(method, path, payload=None):
        assert method == "POST"
        assert path == "/api/chat"
        return {"message": {"role": "assistant", "content": "hello"}}

    monkeypatch.setattr(ollama_api, "API_AUTH_TOKEN", "secret")
    monkeypatch.setattr(ollama_api, "ollama_request", fake_ollama_request)

    payload = {
        "model": "llama3.1:8b",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.7,
        "max_tokens": 64,
    }

    unauthorized = client.post("/chat", json=payload)
    assert unauthorized.status_code == 401
    assert unauthorized.json()["detail"] == "Unauthorized"

    authorized = client.post("/chat", json=payload, headers={"X-API-Key": "secret"})
    assert authorized.status_code == 200
    assert authorized.json()["message"]["content"] == "hello"
