import re
from typing import Any


# ---------------------------------------------------------------------------
# Constants & Regex Patterns
# ---------------------------------------------------------------------------

# Website ke unwanted elements (noise) ko filter karne ke liye patterns
NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bcookie(s)?\b",
        r"\bprivacy\s*policy\b",
        r"\bterms\s*(of\s*(service|use))?\b",
        r"\baccept\b",
        r"\bsubscribe\b",
        r"\bnewsletter\b",
        r"\bcopyright\b",
        r"\ball\s+rights\s+reserved\b",
        r"\bfooter\b",
        r"\bskip\s+to\s+(main\s+)?content\b",
        r"\bback\s+to\s+top\b",
        r"\bscroll\s+down\b",
        r"\bread\s+more\b",
        r"\blearn\s+more\b",
        r"\bclick\s+here\b",
        r"\bsign\s+up\b",
        r"\blog\s+in\b",
        r"\blog\s+out\b",
        r"\bclose\b",
        r"\bmenu\b",
        r"\bnavigation\b",
        r"\bsitemap\b",
    ]
]

# Navigational junk links ko spot karne ke liye patterns
INVALID_URL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^#",
        r"^javascript:",
        r"^mailto:",
        r"^tel:",
        r"^void\(",
        r"^\s*$",
    ]
]

JUNK_CHARS_RE = re.compile(r"[|<>{}\[\]\\]")
MULTI_SPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Low-Level Text Helpers
# ---------------------------------------------------------------------------

def _clean_text(value: Any) -> str:
    """Normalize a single text value into clean readable format."""
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return ""

    # Remove newlines/tabs → convert to single space
    value = value.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    # Strip layout junk characters like |, <, >, {, }, etc.
    value = JUNK_CHARS_RE.sub("", value)
    # Collapse multiple spaces into one
    value = MULTI_SPACE_RE.sub(" ", value).strip()
    return value


def _is_meaningful(text: str) -> bool:
    """Return True only if text carries real cinematic content."""
    if not text or len(text) < 2:
        return False
    # Only whitespace or symbols/punctuation patterns are dropped
    if re.fullmatch(r"[\W\d]+", text):
        return False
    # Check if text matches any layout noise (like Cookie Banner text)
    for pattern in NOISE_PATTERNS:
        if pattern.search(text):
            return False
    return True


def _is_valid_url(url: Any) -> bool:
    """Return True if the URL is navigable and non-trivial."""
    if not isinstance(url, str):
        return False
    url = url.strip()
    for pattern in INVALID_URL_PATTERNS:
        if pattern.match(url):
            return False
    return bool(url)


# ---------------------------------------------------------------------------
# Collection-Level Cleaners
# ---------------------------------------------------------------------------

def _clean_text_list(items: Any) -> list[str]:
    """Clean and deduplicate a list of text strings (buttons/lists)."""
    if not isinstance(items, list):
        return []

    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        cleaned = _clean_text(item)
        if not _is_meaningful(cleaned):
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)

    return result


def _clean_headings(headings: Any) -> dict[str, list[str]]:
    """Clean h1/h2/h3 heading groups, preserving structure."""
    if not isinstance(headings, dict):
        return {"h1": [], "h2": [], "h3": []}

    return {
        level: _clean_text_list(headings.get(level, []))
        for level in ("h1", "h2", "h3")
    }


def _clean_links(links: Any) -> list[dict[str, str]]:
    """Clean link objects, removing noise and invalid entries."""
    if not isinstance(links, list):
        return []

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []

    for link in links:
        if not isinstance(link, dict):
            continue

        text = _clean_text(link.get("text", ""))
        url = _clean_text(link.get("url", ""))

        if not _is_meaningful(text):
            continue
        if not _is_valid_url(url):
            continue

        key = (text.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append({"text": text, "url": url})

    return result


def _clean_title(title: Any) -> str:
    """Clean the page title safely."""
    cleaned = _clean_text(title)
    return cleaned if _is_meaningful(cleaned) else ""


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------

def clean_website_data(data: dict) -> dict:
    """
    Clean raw website extraction output for AI video scene generation.

    Args:
        data: Raw structured data from Playwright legacy output.

    Returns:
        Fully cleaned dictionary with no noise, duplicates, or empty values.
    """
    if not isinstance(data, dict):
        return {
            "title": "",
            "heading": {"h1": [], "h2": [], "h3": []},
            "buttons": [],
            "links": [],
        }

    return {
        "title": _clean_title(data.get("title")),
        "heading": _clean_headings(data.get("heading")),
        "buttons": _clean_text_list(data.get("buttons")),
        "links": _clean_links(data.get("links")),
    }


# ---------------------------------------------------------------------------
# Quick Smoke Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    sample = {
        "title": "  My   Awesome\t\tPortfolio  ",
        "heading": {
            "h1": ["Welcome to My Portfolio", "Welcome to My Portfolio", "  "],
            "h2": ["About Me", "Cookie Policy", "Projects", "About Me"],
            "h3": ["React", None, "|", "Python", "Terms of Service"],
        },
        "buttons": [
            "Accept",
            "Subscribe",
            "View Projects",
            "View Projects",
            "Download CV",
            "",
            "x",
        ],
        "links": [
            {"text": "Home", "url": "#"},
            {"text": "GitHub", "url": "https://github.com/sumit"},
            {"text": "Privacy Policy", "url": "https://example.com/privacy"},
            {"text": "Projects", "url": "javascript:void(0)"},
            {"text": "LinkedIn", "url": "https://linkedin.com/in/sumit"},
            {"text": "GitHub", "url": "https://github.com/sumit"},
            {"text": "", "url": "https://example.com"},
            {"text": "Blog", "url": ""},
        ],
    }

    cleaned = clean_website_data(sample)
    print(json.dumps(cleaned, indent=2))