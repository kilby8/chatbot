import hmac
import os
from typing import List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


def _int_env(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


MAX_MESSAGES = _int_env("CHAT_MAX_MESSAGES", 100, 1)
MAX_MESSAGE_CHARS = _int_env("CHAT_MAX_MESSAGE_CHARS", 8000, 1)
MAX_TOTAL_CHARS = _int_env("CHAT_MAX_TOTAL_CHARS", 50000, 1)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    model: str = Field(default="llama3.1:8b", min_length=1, max_length=120)
    messages: List[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class ChatResponse(BaseModel):
    model: str
    message: ChatMessage


app = FastAPI(title="Local Ollama API", version="1.0.0")

allow_origins = [x.strip() for x in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if x.strip()]
allow_all_origins = len(allow_origins) == 1 and allow_origins[0] == "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    # Browsers ignore wildcard origins when credentials are enabled.
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "").strip()


def _enforce_api_key(x_api_key: Optional[str]) -> None:
    if not API_AUTH_TOKEN:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, API_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def ollama_request(method: str, path: str, payload: Optional[dict] = None) -> dict:
    url = f"{OLLAMA_BASE_URL}{path}"
    timeout = httpx.Timeout(connect=5.0, read=300.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method.upper() == "GET":
                res = await client.get(url)
            else:
                res = await client.request(method.upper(), url, json=payload or {})
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Cannot reach Ollama at {OLLAMA_BASE_URL}. Is 'ollama serve' running?",
            ) from exc

    if res.status_code >= 400:
        detail: Optional[str] = None
        try:
            detail = res.json().get("error")
        except Exception:
            detail = res.text or "Ollama request failed"
        status_code = 400 if 400 <= res.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=detail)

    return res.json()


@app.get("/health")
def health():
    return {"ok": True, "ollama_base_url": OLLAMA_BASE_URL}


@app.get("/models")
async def models(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    _enforce_api_key(x_api_key)
    data = await ollama_request("GET", "/api/tags")
    return {"models": data.get("models", [])}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    _enforce_api_key(x_api_key)
    total_chars = sum(len(m.content) for m in req.messages)
    if total_chars > MAX_TOTAL_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Total message content too large. Max characters: {MAX_TOTAL_CHARS}",
        )

    payload = {
        "model": req.model,
        "messages": [m.model_dump() for m in req.messages],
        "stream": False,
        "options": {
            "temperature": req.temperature,
            "num_predict": req.max_tokens,
        },
    }

    data = await ollama_request("POST", "/api/chat", payload)
    message = data.get("message")
    if not message or "content" not in message:
        raise HTTPException(status_code=500, detail="Invalid response from Ollama")

    return ChatResponse(model=req.model, message=ChatMessage(**message))
