"""Fetch and extract text from web pages."""

import re

import httpx
from bs4 import BeautifulSoup

BLOCK_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}
WHITESPACE_RE = re.compile(r"\s+")


def fetch_url_text(url: str, exclude_domains: list[str] | None = None) -> str:
    if exclude_domains:
        from urllib.parse import urlparse

        host = urlparse(url).netloc.lower()
        for domain in exclude_domains:
            if domain.strip().lower() in host:
                raise ValueError(f"URL domain is excluded: {host}")

    with httpx.Client(follow_redirects=True, timeout=20.0) as client:
        response = client.get(url, headers={"User-Agent": "PlagifyBot/1.0"})
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(BLOCK_TAGS):
        tag.decompose()

    article = soup.find("article") or soup.find("main") or soup.body
    if article is None:
        raise ValueError("No readable content found at URL")

    text = article.get_text(separator="\n")
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    if len(cleaned.split()) < 10:
        raise ValueError("URL page does not contain enough text to scan")
    return cleaned
