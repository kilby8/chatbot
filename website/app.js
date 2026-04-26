const form = document.getElementById("chat-form");
const statusEl = document.getElementById("status");
const chatLog = document.getElementById("chat-log");
const button = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const apiUrlInput = document.getElementById("api-url");
const apiKeyInput = document.getElementById("api-key");
const modelInput = document.getElementById("model");
const modelList = document.getElementById("model-list");
const apiPill = document.getElementById("api-pill");
const modelsPill = document.getElementById("models-pill");

let chatHistory = [];

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#9e1b1b" : "var(--muted)";
}

function appendBubble(role, text) {
  const bubble = document.createElement("article");
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setPill(el, text, state) {
  el.textContent = text;
  el.className = `pill ${state}`;
}

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function chatWithOllama(payload, apiBaseUrl, timeoutMs, retries) {
  const apiKey = apiKeyInput.value.trim();
  const authHeaders = apiKey ? { "X-API-Key": apiKey } : {};
  const attempts = retries + 1;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetchWithTimeout(
        `${apiBaseUrl}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders },
          body: JSON.stringify(payload),
        },
        timeoutMs,
      );

      if (!response.ok) {
        const maybeJson = await response.json().catch(() => null);
        const detail = maybeJson?.detail || `HTTP ${response.status}`;
        throw new Error(detail);
      }

      return response.json();
    } catch (error) {
      const isLastAttempt = attempt === attempts;
      if (isLastAttempt) {
        if (error?.name === "AbortError") {
          throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
        }
        throw error;
      }

      setStatus(`Attempt ${attempt} failed, retrying...`);
    }
  }

  throw new Error("Request failed");
}

async function checkApiHealth(apiBaseUrl) {
  const apiKey = apiKeyInput.value.trim();
  const authHeaders = apiKey ? { "X-API-Key": apiKey } : {};
  const response = await fetchWithTimeout(
    `${apiBaseUrl}/health`,
    { method: "GET", headers: authHeaders },
    5000,
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function loadModels(apiBaseUrl) {
  const apiKey = apiKeyInput.value.trim();
  const authHeaders = apiKey ? { "X-API-Key": apiKey } : {};
  const response = await fetch(`${apiBaseUrl}/models`, { headers: authHeaders });
  if (!response.ok) {
    throw new Error(`Could not load models (HTTP ${response.status})`);
  }

  const data = await response.json();
  const modelNames = (data.models || [])
    .map((item) => (typeof item === "string" ? item : item?.name))
    .filter(Boolean);

  modelList.innerHTML = "";
  for (const name of modelNames) {
    const option = document.createElement("option");
    option.value = name;
    modelList.appendChild(option);
  }

  if (modelNames.length > 0 && !modelInput.value.trim()) {
    modelInput.value = modelNames[0];
  }

  return modelNames.length;
}

async function refreshModels() {
  const apiBaseUrl = apiUrlInput.value.trim().replace(/\/$/, "");
  if (!apiBaseUrl) {
    setPill(apiPill, "API: missing URL", "warn");
    setPill(modelsPill, "Models: -", "unknown");
    return;
  }

  try {
    await checkApiHealth(apiBaseUrl);
    setPill(apiPill, "API: online", "ok");

    const count = await loadModels(apiBaseUrl);
    if (count > 0) {
      setPill(modelsPill, `Models: ${count}`, "ok");
      setStatus(`Loaded ${count} model${count === 1 ? "" : "s"}.`);
    } else {
      setPill(modelsPill, "Models: 0", "warn");
      setStatus("No models found. Pull one with: ollama pull <model>", true);
    }
  } catch (error) {
    setPill(apiPill, "API: offline", "error");
    setPill(modelsPill, "Models: unknown", "unknown");
    setStatus(`Model lookup failed: ${error.message}`, true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const apiBaseUrl = apiUrlInput.value.trim().replace(/\/$/, "");
  const model = modelInput.value.trim();
  const systemPrompt = document.getElementById("system").value.trim();
  const text = document.getElementById("text").value.trim();
  const temperature = Number(document.getElementById("temperature").value);
  const max_tokens = Number(document.getElementById("max-tokens").value);
  const timeoutSeconds = Number(document.getElementById("request-timeout").value);
  const retries = Number(document.getElementById("retries").value);

  if (!text) {
    setStatus("Message is required.", true);
    return;
  }

  if (!model) {
    setStatus("Model is required.", true);
    return;
  }

  if (chatHistory.length === 0) {
    chatLog.innerHTML = "";
  }

  appendBubble("user", text);
  chatHistory.push({ role: "user", content: text });

  const payload = {
    model,
    messages: [
      ...(systemPrompt ? [{ role: "system", content: systemPrompt }] : []),
      ...chatHistory,
    ],
    temperature,
    max_tokens,
  };

  button.disabled = true;
  setStatus("Waiting for local model...");

  try {
    const timeoutMs = Math.max(5000, Math.floor(timeoutSeconds * 1000));
    const safeRetries = Math.min(5, Math.max(0, Math.floor(retries)));
    const result = await chatWithOllama(payload, apiBaseUrl, timeoutMs, safeRetries);
    appendBubble("assistant", result.message.content);
    chatHistory.push({ role: "assistant", content: result.message.content });
    document.getElementById("text").value = "";

    setStatus(`Done at ${new Date().toLocaleTimeString()}.`);
  } catch (error) {
    setStatus(`Generation failed: ${error.message}`, true);
    setPill(apiPill, "API: check connection", "warn");
  } finally {
    button.disabled = false;
  }
});

clearBtn.addEventListener("click", () => {
  chatHistory = [];
  chatLog.innerHTML = "<article class=\"bubble assistant\">Ready. Send your first message.</article>";
  setStatus("Chat cleared.");
});

apiUrlInput.addEventListener("change", refreshModels);
apiKeyInput.addEventListener("change", refreshModels);
window.addEventListener("load", refreshModels);
