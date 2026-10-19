"""What a folder is for: its README's first heading and first paragraph, read once per mtime."""

from __future__ import annotations

import os
import re

README_NAMES = ("README.md", "readme.md", "README", "README.txt", "README.rst")
MAX_CHARS = 160
MAX_BYTES = 64 * 1024


def _clean(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)                 # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)              # links -> their text
    text = re.sub(r"[`*_>#]+", "", text)                             # markdown marks
    text = re.sub(r"<[^>]+>", "", text)                              # html tags
    return re.sub(r"\s+", " ", text).strip()


def parse_readme(text: str) -> str | None:
    """"<first heading> · <first paragraph>", or one of them, cut to MAX_CHARS; None when empty."""
    heading = None
    paragraph: list[str] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if heading is None:
            if line.startswith("#"):
                heading = _clean(line)
                continue
            if not line:
                continue
        if line.startswith("|") or line.startswith("#") or line.startswith("---") or line.startswith("<!--"):
            if paragraph:
                break
            continue
        if not line:
            if paragraph:
                break
            continue
        paragraph.append(line)
    para = _clean(" ".join(paragraph))
    parts = [p for p in (heading, para) if p]
    if not parts:
        return None
    out = " · ".join(parts)
    return out if len(out) <= MAX_CHARS else out[: MAX_CHARS - 1].rstrip() + "…"


def readme_path(folder: str) -> str | None:
    for name in README_NAMES:
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            return p
    return None


class ReadmeCache:
    """folder -> purpose, re-read only when the README's mtime or size changes."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[tuple, str | None]] = {}

    def purpose(self, folder: str) -> str | None:
        path = readme_path(folder)
        if path is None:
            self._cache.pop(folder, None)
            return None
        try:
            st = os.stat(path)
        except OSError:
            return None
        key = (path, st.st_mtime, st.st_size)
        hit = self._cache.get(folder)
        if hit is not None and hit[0] == key:
            return hit[1]
        try:
            with open(path, "rb") as f:
                text = f.read(MAX_BYTES).decode("utf-8", "replace")
        except OSError:
            text = ""
        value = parse_readme(text)
        self._cache[folder] = (key, value)
        return value


def write_readme(folder: str, purpose: str) -> str | None:
    """Create a minimal README.md with the purpose. Never touches an existing README. Returns the path."""
    if readme_path(folder) is not None:
        return None
    path = os.path.join(folder, "README.md")
    with open(path, "x", encoding="utf-8") as f:
        f.write(f"# {os.path.basename(folder.rstrip('/'))}\n\n{purpose.strip()}\n")
    return path
