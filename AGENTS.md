# AGENTS.md

## Repository overview
- Main Python app remains at repo root.
- Solar scraping project lives in `solar_scraper/`.

## Cursor Cloud specific instructions
- Use `python3` for commands in this environment (the `python` alias may not exist).
- Default working directory for solar tasks: `/workspace/solar_scraper`.
- Install dependencies with:
  - `python3 -m pip install -r /workspace/solar_scraper/requirements.txt`
- Keep runtime artifacts in `solar_scraper/solar_data/` (auto-created by scripts).

### Solar scraper run order
1. Build/update DB:
   - `python3 /workspace/solar_scraper/solar_scraper_with_db.py`
2. Run standalone query script:
   - `python3 /workspace/solar_scraper/queries.py`
3. Run interactive CLI:
   - `python3 /workspace/solar_scraper/cli.py`

### Quick validation commands
- `python3 -m py_compile /workspace/solar_scraper/db_manager.py /workspace/solar_scraper/solar_scraper.py /workspace/solar_scraper/solar_scraper_with_db.py /workspace/solar_scraper/cli.py /workspace/solar_scraper/queries.py`

## Notes for local PyCharm users
- Open `solar_scraper/` as the PyCharm project root.
- Set run configuration working directory to that same `solar_scraper/` root.
- For `cli.py`, enable "Emulate terminal in output console" so `input()` works.
