# AGENTS.md

## Cursor Cloud specific instructions

This repository contains two products:

1. **Streamlit Chatbot** (`streamlit_app.py`) — OpenAI GPT-3.5 chat UI on port 8501.
2. **Solar Scraper** (`solar_scraper/`) — web scraper + SQLite DB for solar panel manufacturer/product data.

### Environment basics

- **Python 3.12** is the system Python. The `python` command is symlinked to `python3` (`/usr/bin/python`).
- `pip install --user` puts binaries into `~/.local/bin` (already on `PATH` via `~/.bashrc`).
- There is no test suite, linter config, or build step in this repository.

### Streamlit Chatbot

```
streamlit run streamlit_app.py --server.enableCORS false --server.enableXsrfProtection false --server.headless true
```

Runs on port **8501**. Requires a valid **OpenAI API key** in the UI (or `.streamlit/secrets.toml`).

### Solar Scraper

Dependencies: `solar_scraper/requirements.txt` (installed by the update script).

Scripts must be run from the `solar_scraper/` directory (they use relative imports via `sys.path` in `db_manager.py`):

```bash
cd /workspace/solar_scraper
python solar_scraper_with_db.py   # scrape + populate SQLite DB
python queries.py                 # run all query reports
python cli.py                     # interactive CLI (requires TTY)
```

Key caveats:
- The `solar_data/` directory (for SQLite DB, logs, CSV exports, HTML reports) is created automatically by `db_manager.py`, but `solar_scraper.py` initializes a logger at module import time that expects the directory to exist. If you see `FileNotFoundError` for `scraper.log`, run `mkdir -p solar_scraper/solar_data/reports` first.
- `cli.py` is interactive (uses `input()`); do not run it from non-TTY contexts.
