SHELL := /bin/bash

COMPOSE := docker compose

.PHONY: up up-gpu down down-volumes pull-model ps logs test chat-health models smoke

up:
	$(COMPOSE) up -d --build

up-gpu:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

down:
	$(COMPOSE) down

down-volumes:
	$(COMPOSE) down -v

pull-model:
	@if [[ -z "$(MODEL)" ]]; then echo "Usage: make pull-model MODEL=llama3.2:1b"; exit 1; fi
	$(COMPOSE) exec ollama ollama pull "$(MODEL)"

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=100

test:
	pytest -q

chat-health:
	curl -sS http://localhost:8000/health

models:
	curl -sS http://localhost:8000/models

smoke:
	@echo "[1/3] Checking API health..."
	@curl -fsS http://localhost:8000/health >/dev/null
	@echo "[2/3] Checking model availability..."
	@curl -fsS http://localhost:8000/models | python -c "import json,sys; d=json.load(sys.stdin); assert d.get('models'), 'No models available from /models'"
	@echo "[3/3] Running chat inference smoke test..."
	@MODEL_NAME="$${MODEL:-llama3.2:1b}"; \
	curl -fsS -X POST http://localhost:8000/chat \
		-H 'Content-Type: application/json' \
		-d "{\"model\":\"$$MODEL_NAME\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: smoke-ok\"}],\"temperature\":0,\"max_tokens\":20}" \
		| python -c "import json,sys; d=json.load(sys.stdin); msg=(d.get('message') or {}).get('content','').strip(); assert msg, 'Empty assistant message'; print('assistant:', msg)"
	@echo "Smoke test passed."
