"""Scrape research content from a URL."""
import re


def load_url(url: str) -> tuple[str, str]:
    """Return (content, page_title) from the given URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "requests and beautifulsoup4 are required. Run: pip install requests beautifulsoup4"
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; ResearchOrganizer/1.0; +https://github.com/research-organizer)"
        )
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""

    # Prefer <article> or <main>, fall back to <body>
    body = soup.find("article") or soup.find("main") or soup.body
    if body is None:
        return soup.get_text(separator="\n"), title

    text = body.get_text(separator="\n")
    text = _clean_text(text)
    return text, title


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    # Drop blank-heavy runs
    cleaned = []
    blank_run = 0
    for line in lines:
        if line:
            blank_run = 0
            cleaned.append(line)
        else:
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
    return "\n".join(cleaned).strip()
