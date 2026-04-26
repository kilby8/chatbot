# CSM

**2025/05/20** - CSM is availabile natively in [Hugging Face Transformers](https://huggingface.co/docs/transformers/main/en/model_doc/csm) 🤗 as of version `4.52.1`, more info available [in our model repo](https://huggingface.co/sesame/csm-1b)

**2025/03/13** - We are releasing the 1B CSM variant. The checkpoint is [hosted on Hugging Face](https://huggingface.co/sesame/csm_1b).

---

CSM (Conversational Speech Model) is a speech generation model from [Sesame](https://www.sesame.com) that generates RVQ audio codes from text and audio inputs. The model architecture employs a [Llama](https://www.llama.com/) backbone and a smaller audio decoder that produces [Mimi](https://huggingface.co/kyutai/mimi) audio codes.

A fine-tuned variant of CSM powers the [interactive voice demo](https://www.sesame.com/voicedemo) shown in our [blog post](https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice).

A hosted [Hugging Face space](https://huggingface.co/spaces/sesame/csm-1b) is also available for testing audio generation.

## Requirements

* A CUDA-compatible GPU
* The code has been tested on CUDA 12.4 and 12.6, but it may also work on other versions
* Similarly, Python 3.10 is recommended, but newer versions may be fine
* For some audio operations, `ffmpeg` may be required
* Access to the following Hugging Face models:
  * [Llama-3.2-1B](https://huggingface.co/meta-llama/Llama-3.2-1B)
  * [CSM-1B](https://huggingface.co/sesame/csm-1b)

### Setup

```bash
git clone git@github.com:SesameAILabs/csm.git
cd csm
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Disable lazy compilation in Mimi
export NO_TORCH_COMPILE=1

# You will need access to CSM-1B and Llama-3.2-1B
huggingface-cli login
```

### Windows Setup

The `triton` package cannot be installed in Windows. Instead use `pip install triton-windows`.

## Hugging Face CLI For AI Agents

Use Hugging Face CLI tools to connect coding agents to model search, datasets, Spaces, and jobs.

For complete command details, see the official CLI reference:
https://huggingface.co/docs/huggingface_hub/guides/cli

### Install or update the CLI (project-safe)

```bash
pip install -U huggingface_hub==0.28.1
python -m huggingface_hub.commands.huggingface_cli version
```

Authenticate your session:

```bash
python -m huggingface_hub.commands.huggingface_cli login
```

Token settings:
https://huggingface.co/settings/tokens

### Add the CLI Skill for agents (requires newer hf CLI)

The `hf skills ...` commands require the newer `hf` CLI, which can conflict with this repo's Python dependencies if installed directly in the same environment.
Use an isolated environment for those commands.

Helper script in this repo:

```bash
bash scripts/setup_hf_cli.sh --global
```

Project-local skills:

```bash
bash scripts/setup_hf_cli.sh --project
```

Claude mode:

```bash
bash scripts/setup_hf_cli.sh --claude --global
```

Setup only (no skill install):

```bash
bash scripts/setup_hf_cli.sh --no-skills
```

Run `hf` without manual activation:

```bash
bash scripts/hf.sh --help
bash scripts/hf.sh auth login
```

The wrapper auto-bootstraps the isolated venv if missing, then forwards all args to `hf`.

Example (separate environment):

```bash
python -m venv ~/.venvs/hf-cli
source ~/.venvs/hf-cli/bin/activate
pip install -U huggingface_hub
hf --version
```

Global install (all projects):

```bash
hf skills add --global
```

For Claude Code:

```bash
hf skills add --claude --global
```

Project-local install:

```bash
hf skills add
```

Project-local for Claude Code:

```bash
hf skills add --claude
```

Alternative via Claude plugin commands:

```bash
claude
/plugin marketplace add huggingface/skills
/plugin install hf-cli@huggingface/skills
```

### Useful commands for this repository

```bash
python -m huggingface_hub.commands.huggingface_cli whoami
python -m huggingface_hub.commands.huggingface_cli repo --help
python -m huggingface_hub.commands.huggingface_cli upload --help
```

Jobs documentation:
https://huggingface.co/docs/huggingface_hub/guides/cli#hf-jobs

## Quickstart

This script will generate a conversation between 2 characters, using a prompt for each character.

```bash
python run_csm.py
```

## Move To Ollama (Local)

This repository now includes a local Ollama backend and a website chat UI.

## Run With Docker + Ollama

This is the fastest way to run the chat stack with an LLM.

### 1) Start containers

```bash
docker compose up -d --build
```

If you have an NVIDIA GPU and Docker GPU runtime configured:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

This starts:

- Ollama runtime at `http://localhost:11434`
- FastAPI bridge at `http://localhost:8000`
- Web UI at `http://localhost:8080`

The compose file also defines healthchecks and waits for healthy dependencies (`ollama` -> `api` -> `web`).

### 2) Pull an LLM into Ollama

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

You can replace `llama3.1:8b` with any Ollama model name you want.

### 3) Verify model visibility

```bash
curl http://localhost:8000/models
```

Optional inference smoke test:

```bash
curl -X POST http://localhost:8000/chat \
    -H 'Content-Type: application/json' \
    -d '{
        "model": "llama3.2:1b",
        "messages": [{"role": "user", "content": "Reply with exactly: docker-connected"}],
        "temperature": 0,
        "max_tokens": 30
    }'
```

### 4) Open the chat UI

Visit `http://localhost:8080` in your browser. The model field will auto-suggest available Ollama models.

### 5) Stop services

```bash
docker compose down
```

To also remove downloaded model data:

```bash
docker compose down -v
```

### Optional Makefile shortcuts

```bash
make up
make up-gpu
make pull-model MODEL=llama3.2:1b
make ps
make chat-health
make models
make smoke
make down
```

Use a specific model for smoke test:

```bash
make smoke MODEL=llama3.2:1b
```

### Included files

- `ollama_api.py` (FastAPI proxy to your local Ollama runtime)
- `Dockerfile.ollama-api` (container image for the API bridge)
- `docker-compose.yml` (Ollama + API + Web stack)
- `website/index.html`
- `website/styles.css`
- `website/app.js`

### 1) Install and start Ollama

On your machine, install Ollama and run:

```bash
ollama serve
```

In a second terminal, pull a model (example):

```bash
ollama pull llama3.1:8b
```

### 2) Start the local API bridge

```bash
pip install -r requirements.txt
export CORS_ALLOW_ORIGINS=http://localhost:8080
export OLLAMA_BASE_URL=http://127.0.0.1:11434
uvicorn ollama_api:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /models`
- `POST /chat`

Optional request guardrails for `POST /chat` (env vars):

- `CHAT_MAX_MESSAGES` (default `100`)
- `CHAT_MAX_MESSAGE_CHARS` (default `8000`)
- `CHAT_MAX_TOTAL_CHARS` (default `50000`)

Optional API auth (recommended beyond localhost):

- `API_AUTH_TOKEN` (if set, clients must send `X-API-Key: <token>`)

### 3) Serve the website

```bash
cd website
python3 -m http.server 8080
```

Open: `http://localhost:8080`

The page automatically calls `GET /models` and suggests available local models in the **Model** input.
It also shows API/model status badges and lets you tune per-request timeout and retry count from the form.
If auth is enabled, set the API key in the **API Key** field so requests include `X-API-Key`.

### 4) Optional CLI chat client

You can also chat from the terminal:

```bash
python chat.py --api http://127.0.0.1:8000 --model llama3.1:8b
```

Useful reliability flags:

```bash
python chat.py --timeout 120 --retries 2
```

If auth is enabled:

```bash
python chat.py --api-key "$API_AUTH_TOKEN"
```

or via environment variable:

```bash
export API_AUTH_TOKEN=your-token-here
python chat.py
```

One-shot mode:

```bash
python chat.py --oneshot "Write a one-sentence greeting."
```

### 5) Chat request schema

```json
{
  "model": "llama3.1:8b",
  "messages": [
    { "role": "system", "content": "You are a concise and helpful assistant." },
    { "role": "user", "content": "Write a short welcome message." }
  ],
  "temperature": 0.7,
  "max_tokens": 512
}
```

The website calls `http://localhost:8000/chat` by default and keeps conversation context in-browser.

If you set `API_AUTH_TOKEN`, configure your client to include `X-API-Key` on requests.

## Legacy CSM API (Optional)

The previous CSM audio-generation API remains available in `web_api.py` if you still want text-to-speech with enough GPU memory.

## Usage

If you want to write your own applications with CSM, the following examples show basic usage.

#### Generate a sentence

This will use a random speaker identity, as no prompt or context is provided.

```python
from generator import load_csm_1b
import torchaudio
import torch

if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

generator = load_csm_1b(device=device)

audio = generator.generate(
    text="Hello from Sesame.",
    speaker=0,
    context=[],
    max_audio_length_ms=10_000,
)

torchaudio.save("audio.wav", audio.unsqueeze(0).cpu(), generator.sample_rate)
```

#### Generate with context

CSM sounds best when provided with context. You can prompt or provide context to the model using a `Segment` for each speaker's utterance.

NOTE: The following example is instructional and the audio files do not exist. It is intended as an example for using context with CSM.

```python
from generator import Segment

speakers = [0, 1, 0, 0]
transcripts = [
    "Hey how are you doing.",
    "Pretty good, pretty good.",
    "I'm great.",
    "So happy to be speaking to you.",
]
audio_paths = [
    "utterance_0.wav",
    "utterance_1.wav",
    "utterance_2.wav",
    "utterance_3.wav",
]

def load_audio(audio_path):
    audio_tensor, sample_rate = torchaudio.load(audio_path)
    audio_tensor = torchaudio.functional.resample(
        audio_tensor.squeeze(0), orig_freq=sample_rate, new_freq=generator.sample_rate
    )
    return audio_tensor

segments = [
    Segment(text=transcript, speaker=speaker, audio=load_audio(audio_path))
    for transcript, speaker, audio_path in zip(transcripts, speakers, audio_paths)
]
audio = generator.generate(
    text="Me too, this is some cool stuff huh?",
    speaker=1,
    context=segments,
    max_audio_length_ms=10_000,
)

torchaudio.save("audio.wav", audio.unsqueeze(0).cpu(), generator.sample_rate)
```

## FAQ

**Does this model come with any voices?**

The model open-sourced here is a base generation model. It is capable of producing a variety of voices, but it has not been fine-tuned on any specific voice.

**Can I converse with the model?**

CSM is trained to be an audio generation model and not a general-purpose multimodal LLM. It cannot generate text. We suggest using a separate LLM for text generation.

**Does it support other languages?**

The model has some capacity for non-English languages due to data contamination in the training data, but it likely won't do well.

## Misuse and abuse ⚠️

This project provides a high-quality speech generation model for research and educational purposes. While we encourage responsible and ethical use, we **explicitly prohibit** the following:

- **Impersonation or Fraud**: Do not use this model to generate speech that mimics real individuals without their explicit consent.
- **Misinformation or Deception**: Do not use this model to create deceptive or misleading content, such as fake news or fraudulent calls.
- **Illegal or Harmful Activities**: Do not use this model for any illegal, harmful, or malicious purposes.

By using this model, you agree to comply with all applicable laws and ethical guidelines. We are **not responsible** for any misuse, and we strongly condemn unethical applications of this technology.

---

## Authors
Johan Schalkwyk, Ankit Kumar, Dan Lyth, Sefik Emre Eskimez, Zack Hodari, Cinjon Resnick, Ramon Sanabria, Raven Jiang, and the Sesame team.
