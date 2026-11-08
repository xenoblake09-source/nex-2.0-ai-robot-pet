"""Montfort Bagaha school knowledge.

The school website is fetched once per cache window, converted to plain text
and used as grounding context. Nothing here invents facts: if the site cannot
be reached or does not contain the answer, the model is told to say so.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from html.parser import HTMLParser

import httpx

from .config import get_settings

logger = logging.getLogger("nex.school")

_IGNORE_TAGS = {"script", "style", "noscript", "svg", "head"}
_BLOCK_TAGS = {
    "p",
    "div",
    "li",
    "br",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "header",
    "footer",
    "nav",
    "td",
}


class _TextExtractor(HTMLParser):
    """Minimal HTML -> text converter (stdlib only, no extra dependencies)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _IGNORE_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in _IGNORE_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._title = text
        self._chunks.append(text + " ")

    @property
    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n", raw)
        return raw.strip()

    @property
    def title(self) -> str:
        return self._title


# Key sub-pages that carry the real facts about the school. The homepage alone
# is mostly navigation, so we crawl a curated set of pages and merge them.
SCHOOL_PAGES = [
    "https://montfortbagaha.org/",
    "https://montfortbagaha.org/school-information/",
    "https://montfortbagaha.org/our-founder/",
    "https://montfortbagaha.org/management-team/",
    "https://montfortbagaha.org/principals-desk/",
    "https://montfortbagaha.org/smart-classes/",
    "https://montfortbagaha.org/library/",
    "https://montfortbagaha.org/labs-in-general/",
    "https://montfortbagaha.org/computer-lab/",
    "https://montfortbagaha.org/eco-club/",
    "https://montfortbagaha.org/science-and-math-club/",
    "https://montfortbagaha.org/literary-club/",
    "https://montfortbagaha.org/games-sports-club/",
    "https://montfortbagaha.org/teaching-staff/",
    "https://montfortbagaha.org/contact/",
]


class SchoolKnowledge:
    """Cached snapshot of the school website."""

    def __init__(self) -> None:
        self._text: str = ""
        self._title: str = ""
        self._fetched_at: float = 0.0
        self._ok: bool = False
        self._error: str | None = None
        self._pages: list[str] = []
        self._lock = asyncio.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._ok

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def title(self) -> str:
        return self._title

    def _is_fresh(self) -> bool:
        settings = get_settings()
        return self._ok and (time.time() - self._fetched_at) < settings.school_cache_ttl

    async def _fetch(self) -> tuple[str, str]:
        settings = get_settings()
        headers = {
            "User-Agent": "NEX-AIRobotPet/1.0 (+school knowledge bot)",
            "Accept": "text/html,application/xhtml+xml",
        }
        base = settings.school_url.rstrip("/")
        urls = [u if u.startswith("http") else base + u for u in SCHOOL_PAGES]

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0), follow_redirects=True, headers=headers
        ) as client:

            async def grab(url: str) -> tuple[str, str, str]:
                response = await client.get(url)
                response.raise_for_status()
                parser = _TextExtractor()
                parser.feed(response.text)
                return url, parser.title, parser.text

            results = await asyncio.gather(
                *(grab(url) for url in urls), return_exceptions=True
            )

        merged: list[str] = []
        title = ""
        fetched: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                logger.debug("School sub-page failed: %s", result)
                continue
            url, page_title, text = result
            if not text:
                continue
            title = title or page_title
            fetched.append(url)
            merged.append(f"--- {url} ---\n{text}")

        if not merged:
            raise RuntimeError("Could not read any school page.")
        return title, "\n\n".join(merged)

    async def ensure_loaded(self, force: bool = False) -> bool:
        """Load the school site if the cache is cold/stale. Returns success."""
        async with self._lock:
            if not force and self._is_fresh():
                return True
            try:
                title, text = await self._fetch()
            except Exception as exc:  # noqa: BLE001
                self._error = f"{type(exc).__name__}: {exc}"
                logger.warning("School fetch failed: %s", self._error)
                # Keep any previously fetched copy — better than nothing.
                return self._ok
            if not text:
                self._error = "Empty document"
                return self._ok
            self._title = title
            self._text = text
            self._pages = [line[4:] for line in text.splitlines() if line.startswith("--- http")]
            self._fetched_at = time.time()
            self._ok = True
            self._error = None
            logger.info("School knowledge loaded (%d chars)", len(text))
            return True

    def context(self, max_chars: int = 6000) -> str:
        """Return the grounding block for the model."""
        if not self._ok:
            return (
                "SCHOOL FACTS: unavailable right now (the school website could not be "
                "reached). If the user asks about the school, say that you could not "
                "verify the information at this moment and offer to try again."
            )
        body = self._text[:max_chars]
        header = f"SCHOOL FACTS (source: {get_settings().school_url}"
        if self._title:
            header += f", page title: {self._title}"
        header += "):\n"
        return header + body + "\n\nEND SCHOOL FACTS."

    def snapshot(self) -> dict:
        return {
            "loaded": self._ok,
            "title": self._title,
            "chars": len(self._text),
            "pages": len(self._pages),
            "fetched_at": self._fetched_at,
            "error": self._error,
            "source_url": get_settings().school_url,
        }


school_knowledge = SchoolKnowledge()
