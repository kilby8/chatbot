# AGENTS.md

## Cursor Cloud specific instructions

This is a simple Streamlit chatbot app using OpenAI's GPT-3.5-turbo. Single Python file (`streamlit_app.py`), two pip dependencies (`streamlit`, `openai`).

### Running the app

```
streamlit run streamlit_app.py --server.enableCORS false --server.enableXsrfProtection false --server.headless true
```

The app serves on port **8501**. See `README.md` for the canonical setup steps.

### Gotchas

- `~/.local/bin` may not be on `PATH` in cloud VMs. If `streamlit` is not found, run: `export PATH="$HOME/.local/bin:$PATH"` or use `python3 -m streamlit` instead.
- The app requires an OpenAI API key entered via the UI at runtime. Without a key the app loads but cannot generate chat responses. No local secrets/env vars are needed for the app to start.
- There are no automated tests, linter configs, or build steps in this repository.
