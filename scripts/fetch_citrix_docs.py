"""
fetch_citrix_docs.py
====================
Downloads the public Citrix documentation pages listed in docs/sources.txt
and saves each one as Markdown under docs/citrix/<category>/.

Every file starts with a "Source: <url>" line so the solution agent can
cite where an answer came from. Pages that fail to download, are blocked
by robots.txt, or have no readable content are reported and skipped.

Run from the project root:
    python scripts/fetch_citrix_docs.py
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = PROJECT_ROOT / "docs" / "sources.txt"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "citrix"

USER_AGENT = "CitrixHelperPrototype/0.1 (learning project)"
DELAY_SECONDS = 1.5  # be polite to the docs site
MIN_CONTENT_CHARS = 500  # less than this usually means a JS-only or empty page


def read_sources() -> list[tuple[str, str]]:
    """Return (category, url) pairs from sources.txt, skipping comments."""
    sources = []
    for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        category, url = (part.strip() for part in line.split("|", 1))
        sources.append((category, url))
    return sources


def robots_for(url: str, cache: dict[str, RobotFileParser]) -> RobotFileParser:
    origin = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if origin not in cache:
        parser = RobotFileParser(origin + "/robots.txt")
        parser.read()
        cache[origin] = parser
    return cache[origin]


def page_to_markdown(html: str) -> tuple[str, str]:
    """Return (title, markdown body) with navigation and boilerplate removed."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else "Untitled"

    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    # docs.citrix.com puts the article body in .sub-content-main. Everything
    # around it (site menu, translation banners, feedback widgets) would
    # otherwise repeat in every file and pollute search results.
    main = soup.select_one(".sub-content-main") or soup.find("main") or soup.body or soup
    markdown = markdownify(str(main), heading_style="ATX")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return title, markdown


def file_name_for(url: str) -> str:
    """docs.citrix.com/en-us/storefront/current-release/troubleshoot.html
    -> storefront_current-release_troubleshoot.md"""
    path = urlparse(url).path
    path = re.sub(r"^/en-us/", "", path).removesuffix(".html").strip("/")
    return re.sub(r"[^a-zA-Z0-9-]+", "_", path) + ".md"


def main() -> None:
    # docs/citrix is generated output: start clean so pages removed from
    # sources.txt don't linger and get uploaded to the vector store.
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    robots_cache: dict[str, RobotFileParser] = {}
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    saved, skipped = 0, []
    for category, url in read_sources():
        if not robots_for(url, robots_cache).can_fetch(USER_AGENT, url):
            skipped.append((url, "blocked by robots.txt"))
            continue

        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            skipped.append((url, str(exc)))
            continue
        finally:
            time.sleep(DELAY_SECONDS)

        title, body = page_to_markdown(response.text)
        if len(body) < MIN_CONTENT_CHARS:
            skipped.append((url, f"only {len(body)} chars of content (JS-only page?)"))
            continue

        out_path = OUTPUT_DIR / category / file_name_for(url)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            f"Source: {url}\nCategory: {category}\nTitle: {title}\n\n{body}\n",
            encoding="utf-8",
        )
        saved += 1
        print(f"saved   {out_path.relative_to(PROJECT_ROOT)} ({len(body):,} chars)")

    for url, reason in skipped:
        print(f"skipped {url}: {reason}")
    print(f"\n{saved} saved, {len(skipped)} skipped")


if __name__ == "__main__":
    main()
