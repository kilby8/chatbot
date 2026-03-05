## Cursor Cloud specific instructions

This is a single-file Streamlit chatbot app (`streamlit_app.py`) using the OpenAI API. There is no build step, no linter config, and no automated tests in the repo.

### Running the app

```
streamlit run streamlit_app.py --server.enableCORS false --server.enableXsrfProtection false --server.headless true
```

The app runs on **port 8501**. The `--server.headless true` flag is required in headless/cloud environments to suppress the interactive email prompt.

### PATH note

`pip install --user` places executables in `~/.local/bin`, which may not be on `PATH` by default. If `streamlit` is not found, run:

```
export PATH="$HOME/.local/bin:$PATH"
```

### OpenAI API key

The app requires a valid OpenAI API key entered in the UI (or via `.streamlit/secrets.toml`). Without a real key, the chat UI will display an `AuthenticationError` when sending messages — this is expected behavior, not a bug.
