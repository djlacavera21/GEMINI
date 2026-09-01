# GEMINI

**Cloner Tool** — *ClnrToolzforDigitalFoolz*  
Sir Big D & My Crude Digital Toolz

GEMINI is a local public-source cloner. It shallow-clones Git repositories, takes bounded same-host web snapshots, copies local trees, writes a job record, and — when a Gemini API key is present — produces a research brief and a clean-room twin plan.

It automates capture and notes. It does not steal accounts, bypass logins, scrape private systems, or republish other people's proprietary code.

## What it does

- `repo` — `git clone --depth 1` of a public repository, with HEAD / branch / remote captured in `job.json`
- `web` — same-host public page + first-party asset snapshot, robots.txt respected, page and byte caps enforced
- `tree` — copy a local file or directory into the clone root (skips `.git`, `node_modules`, `.venv`)
- `analyze` — Gemini reads sampled text files and writes `ANALYSIS.md`
- `twin` — Gemini writes an original reconstruction brief in `twin/TWIN.md`
- `report` — concatenates job metadata, analysis, and twin into `REPORT.md`
- `doctor` — prints capability, clone root, and whether a Gemini key is loaded

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
gemini-cloner doctor
```

Clone a public repo (Git required on PATH):

```bash
gemini-cloner repo https://github.com/djlacavera21/GEMINI
# or shorthand
gemini-cloner repo djlacavera21/GEMINI
```

Snapshot a public site you are allowed to archive:

```bash
gemini-cloner web https://example.com
```

Copy a local tree:

```bash
gemini-cloner tree ./src
```

Optional Gemini pass — requires `GEMINI_API_KEY` in `.env`:

```bash
gemini-cloner analyze clones/djlacavera21-gemini
gemini-cloner twin clones/djlacavera21-gemini
gemini-cloner report clones/djlacavera21-gemini
```

Jobs land under `clones/` by default:

```text
clones/<slug>/
  job.json
  source/
  ANALYSIS.md          # after analyze
  analysis.json
  twin/TWIN.md         # after twin
  REPORT.md            # after report
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | empty | Required for `analyze` / `twin` |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Public Gemini model id |
| `GEMINI_CLONE_ROOT` | `clones` | Job output root |
| `GEMINI_WEB_MAX_PAGES` | `40` | Web snapshot page cap |
| `GEMINI_WEB_MAX_BYTES` | `8000000` | Web snapshot byte cap |
| `GEMINI_WEB_TIMEOUT` | `20` | Per-request timeout seconds |

Get a key from [Google AI Studio](https://aistudio.google.com/). Never commit the key.

## Safety boundaries

GEMINI never:

- logs into sites, stores cookies, or harvests credentials
- follows off-host links during a web snapshot
- ignores `robots.txt` when the file is reachable
- clones private GitHub repositories unless your local `git` already has credentials you supplied yourself
- ships a proxy, credential dumper, session hijacker, or phishing kit
- treats a twin brief as a license to redistribute third-party source

A twin brief is a clean-room plan for an original project inspired by the source. It is not a byte-for-byte replica and not legal advice.

Web snapshots are for sources you own, sources that invite archiving, or sources whose terms allow research copies. Respect copyright and site terms.

## Tests

```bash
pytest -q
```

CI runs the same suite on every push to `main`.

## Layout

```text
src/gemini_cloner/   CLI and clone engines
tests/               unit tests, no network required
examples/            sample commands
.github/workflows/   pytest + doctor
```

## License

MIT © 2026 Dominic J. LaCavera Jr.
