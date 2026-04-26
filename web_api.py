import base64
import hmac
import os
import tempfile
from typing import List

import torch
import torchaudio
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from generator import Segment, load_csm_1b


class ContextSegment(BaseModel):
    speaker: int = Field(ge=0)
    text: str
    audio_base64_wav: str


class GenerateRequest(BaseModel):
    text: str
    speaker: int = Field(default=0, ge=0)
    max_audio_length_ms: int = Field(default=10_000, ge=1000, le=120_000)
    temperature: float = Field(default=0.9, gt=0.0, le=2.0)
    topk: int = Field(default=50, ge=1, le=500)
    context: List[ContextSegment] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    sample_rate: int
    audio_base64_wav: str


app = FastAPI(title="CSM API", version="1.0.0")

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

API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "").strip()


_generator = None


def _enforce_api_key(x_api_key: str | None) -> None:
    if not API_AUTH_TOKEN:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, API_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_generator():
    global _generator
    if _generator is None:
        _generator = load_csm_1b(device=get_device())
    return _generator


def decode_wav_base64_to_tensor(audio_base64_wav: str, target_sample_rate: int) -> torch.Tensor:
    try:
        wav_bytes = base64.b64decode(audio_base64_wav)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 audio payload") from exc

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        audio, sample_rate = torchaudio.load(tmp.name)

    audio = audio.squeeze(0)
    if sample_rate != target_sample_rate:
        audio = torchaudio.functional.resample(audio, sample_rate, target_sample_rate)
    return audio


def encode_tensor_to_wav_base64(audio: torch.Tensor, sample_rate: int) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        torchaudio.save(tmp.name, audio.unsqueeze(0).cpu(), sample_rate)
        tmp.flush()
        tmp.seek(0)
        wav_bytes = tmp.read()
    return base64.b64encode(wav_bytes).decode("utf-8")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _enforce_api_key(x_api_key)
    generator = get_generator()

    context_segments = []
    for seg in req.context:
        audio_tensor = decode_wav_base64_to_tensor(seg.audio_base64_wav, generator.sample_rate)
        context_segments.append(Segment(speaker=seg.speaker, text=seg.text, audio=audio_tensor))

    try:
        audio = generator.generate(
            text=req.text,
            speaker=req.speaker,
            context=context_segments,
            max_audio_length_ms=req.max_audio_length_ms,
            temperature=req.temperature,
            topk=req.topk,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Audio generation failed") from exc

    return GenerateResponse(
        sample_rate=generator.sample_rate,
        audio_base64_wav=encode_tensor_to_wav_base64(audio, generator.sample_rate),
    )
