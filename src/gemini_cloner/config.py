from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from gemini_cloner.util import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    clone_root: Path
    web_max_pages: int
    web_max_bytes: int
    web_timeout: float
    user_agent: str


def settings() -> Settings:
    load_dotenv()
    root = Path(os.environ.get("GEMINI_CLONE_ROOT", "clones")).expanduser()
    return Settings(
        api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
        clone_root=root,
        web_max_pages=int(os.environ.get("GEMINI_WEB_MAX_PAGES", "40")),
        web_max_bytes=int(os.environ.get("GEMINI_WEB_MAX_BYTES", "8000000")),
        web_timeout=float(os.environ.get("GEMINI_WEB_TIMEOUT", "20")),
        user_agent=os.environ.get(
            "GEMINI_USER_AGENT",
            "GEMINI-Cloner/0.1 (+https://github.com/djlacavera21/GEMINI; research-archive)",
        ),
    )
