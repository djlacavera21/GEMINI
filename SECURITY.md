# Security

GEMINI is a local research cloner. Treat every clone directory as untrusted input.

## Do not commit

- `.env` or any `GEMINI_API_KEY`
- cookies, session tokens, SSH keys, or GitHub PATs
- private repository contents you are not allowed to publish
- scraped personal data

## Threat notes

- A cloned repository can contain malicious install scripts. Do not run `make`, `npm install`, or random binaries from `source/` until you have read them.
- Web snapshots can contain active JavaScript. Open `source/` HTML as files, not as a trusted origin.
- The Gemini prompt only receives sampled text excerpts. Still: do not point `analyze` at directories that hold secrets.

## Reporting

Open a private advisory or an issue on https://github.com/djlacavera21/GEMINI if you find a defect that causes credential leakage, path traversal outside the clone root, or unbounded network fetch.
