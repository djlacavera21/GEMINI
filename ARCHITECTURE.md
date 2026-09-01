# Architecture

```text
CLI (gemini-cloner)
  ├── repo  → git_clone.clone_repo   → clones/<slug>/source + job.json
  ├── web   → web_clone.clone_web    → same-host bounded snapshot
  ├── tree  → tree_clone.clone_tree  → local copy
  ├── analyze → inventory + Gemini generateContent → ANALYSIS.md
  ├── twin    → Gemini reconstruction brief        → twin/TWIN.md
  └── report  → markdown rollup                    → REPORT.md
```

## Design rules

1. Every successful clone writes `job.json` before any model call.
2. Gemini is optional. Capture works without a key.
3. Web fetch is same-host only, robots-aware, and hard-capped.
4. Analyze samples text files; it does not upload whole trees.
5. Twin output is a plan document, not a generated proprietary dump.

## Gemini transport

`gemini.py` posts to the public Generative Language API:

`POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=...`

No official SDK is required. `httpx` is the only runtime dependency.

## Failure modes

| Case | Behavior |
|---|---|
| `git` missing | `repo` exits 2 |
| clone dir exists | refuse to overwrite |
| no API key | `analyze` / `twin` exits 2 |
| robots.txt deny | URL recorded in `errors`, not fetched |
| page/byte cap | snapshot stops, partial job is valid |
