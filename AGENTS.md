# AGENTS.md

## Cursor Cloud specific instructions

This is a single-file Streamlit chatbot app (`streamlit_app.py`) that uses OpenAI's GPT-3.5-turbo API.

### Running the app

```
streamlit run streamlit_app.py --server.enableCORS false --server.enableXsrfProtection false --server.headless true
```

The app runs on port **8501**. See `README.md` for basic setup instructions.

### Key caveats

- `pip install --user` installs binaries to `~/.local/bin`. Ensure this is on your `PATH` (already configured in `~/.bashrc`).
- The app requires a valid **OpenAI API key** entered in the UI (or via `.streamlit/secrets.toml`) to generate chat responses. Without it, the app loads but chat messages will fail with an `AuthenticationError`.
- There is no test suite, linter config, or build step in this repository. The only verification is running the Streamlit dev server and confirming it serves the UI.
