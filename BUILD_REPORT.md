# Build report — GEMINI 0.1.0

Date: 2026-09-01

The repository was an empty stub (`README.md` only: "ClnrToolzforDigitalFoolz"). This build turns it into an installable Python CLI.

## Shipped

- `gemini-cloner` / `gemini` console scripts
- Public Git shallow clone
- Bounded same-host web snapshot with robots.txt
- Local tree copy
- Optional Gemini analysis and clean-room twin brief
- Job / analysis / report artifacts
- pytest suite (no network)
- GitHub Actions CI
- MIT license, security note, architecture note

## Not shipped (on purpose)

- Login automation
- Cookie jars
- Private-API scrapers
- Site-wide unrestricted crawlers
- Binary redistribution helpers

## Verify locally

```bash
python -m pip install -e '.[dev]'
pytest -q
gemini-cloner doctor
```
