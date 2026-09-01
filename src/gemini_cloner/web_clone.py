from __future__ import annotations

from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from gemini_cloner.config import Settings
from gemini_cloner.util import ensure_dir, host_from_url, is_http_url, same_host, slugify, utc_now, write_json


class CloneError(RuntimeError):
    pass


HREF_ATTRS = {"href", "src"}
SKIP_SCHEMES = {"mailto", "javascript", "data", "tel"}
ASSET_EXT = {
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
}


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in HREF_ATTRS and value:
                self.links.append(value)


def extract_links(html: str, base: str) -> list[str]:
    parser = LinkExtractor()
    try:
        parser.feed(html)
    except Exception:
        return []
    out: list[str] = []
    for raw in parser.links:
        absolute, _ = urldefrag(urljoin(base, raw))
        parsed = urlparse(absolute)
        if parsed.scheme in SKIP_SCHEMES:
            continue
        if parsed.scheme in {"http", "https"}:
            out.append(absolute)
    return out


def local_path_for(url: str, root: Path) -> Path:
    parsed = urlparse(url)
    path = parsed.path
    if path.endswith("/") or path == "":
        path = path + "index.html"
    if "." not in Path(path).name:
        path = path.rstrip("/") + "/index.html"
    safe = Path(*[slugify(part, "x") for part in path.split("/") if part])
    target = root / "source" / safe
    return target


def robots_allows(client: httpx.Client, start_url: str, user_agent: str) -> RobotFileParser:
    parsed = urlparse(start_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        response = client.get(robots_url)
        parser.parse(response.text.splitlines() if response.status_code == 200 else [])
    except httpx.HTTPError:
        parser.parse([])
    return parser


def clone_web(url: str, dest_root: Path, settings: Settings) -> dict:
    if not is_http_url(url):
        raise CloneError(f"Only http(s) URLs can be snapshotted: {url}")

    job_dir = ensure_dir(dest_root / slugify(host_from_url(url)))
    source_root = ensure_dir(job_dir / "source")
    headers = {"User-Agent": settings.user_agent, "Accept": "*/*"}
    fetched: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()
    queue: deque[str] = deque([url])
    total_bytes = 0

    with httpx.Client(follow_redirects=True, timeout=settings.web_timeout, headers=headers) as client:
        robots = robots_allows(client, url, settings.user_agent)
        while queue and len(fetched) < settings.web_max_pages and total_bytes < settings.web_max_bytes:
            current = queue.popleft()
            if current in seen or not same_host(url, current):
                continue
            seen.add(current)
            if robots.entries and not robots.can_fetch(settings.user_agent, current):
                errors.append({"url": current, "error": "robots.txt disallowed"})
                continue
            try:
                response = client.get(current)
            except httpx.HTTPError as exc:
                errors.append({"url": current, "error": str(exc)})
                continue
            body = response.content
            total_bytes += len(body)
            dest = local_path_for(str(response.url), job_dir)
            ensure_dir(dest.parent)
            dest.write_bytes(body)
            record = {
                "url": str(response.url),
                "status": response.status_code,
                "bytes": len(body),
                "path": str(dest.relative_to(job_dir)),
                "content_type": response.headers.get("content-type", ""),
            }
            fetched.append(record)
            content_type = record["content_type"].lower()
            if "html" in content_type or dest.suffix in {".html", ".htm"}:
                try:
                    text = body.decode(response.encoding or "utf-8", errors="ignore")
                except LookupError:
                    text = body.decode("utf-8", errors="ignore")
                for link in extract_links(text, str(response.url)):
                    if link in seen or not same_host(url, link):
                        continue
                    parsed = urlparse(link)
                    suffix = Path(parsed.path).suffix.lower()
                    if suffix in ASSET_EXT or suffix in {"", ".html", ".htm"}:
                        queue.append(link)

    meta = {
        "kind": "web",
        "source": url,
        "created_at": utc_now(),
        "pages": len(fetched),
        "bytes": total_bytes,
        "errors": errors[:50],
        "fetched": fetched,
        "worktree": str(source_root),
        "robots_checked": True,
    }
    write_json(job_dir / "job.json", meta)
    return meta
