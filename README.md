# GEMINI

**Cloner Tool** — *ClnrToolzforDigitalFoolz*  
Sir Big D & My Crude Digital Toolz

GEMINI is an owner-authorized cloner with a push-button command-line menu.

The headline job is: tell an operator to clone this phone from the CLI, and it only proceeds after the owner approves a short-lived link on that phone. The SMS carries the link. The passkey stays on the phone and signs the job challenge. Android RSA / iPhone "Trust This Computer" is still required. Remote consent does not replace the phone OS data-access prompt.

```bash
pip install -e '.[dev]'
gemini-cloner                 # interactive menu
gemini-cloner phone detect
gemini-cloner phone serve
gemini-cloner phone request --phone +15555550100 --scope media,documents,packages
gemini-cloner phone status <job_id>
gemini-cloner phone clone <job_id>        # dry-run
gemini-cloner phone clone <job_id> --live
```

See [docs/PHONE_CLONE.md](docs/PHONE_CLONE.md).

Public Git/web/tree capture remains available: `repo`, `web`, `tree`, `analyze`, `twin`.

MIT © 2026 Dominic J. LaCavera Jr.
