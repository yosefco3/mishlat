"""Mishlat's own files. Writes are atomic (temp file + rename) and private (mode 0600)."""

from __future__ import annotations

import json
import os

from . import paths
from .model import INDEX_VERSION, OLD_DAYS
from .strings import LANGS, locale_lang

FONT_DEFAULT, FONT_MIN, FONT_MAX = 15, 12, 24
CACHE_VERSION = 3  # 3: transcripts carry last_ts (content time) besides writes / reads


def write_json(path: str, obj, mode: int = 0o600) -> None:
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def read_index(home: str) -> dict | None:
    obj = read_json(paths.index_path(home))
    return obj if isinstance(obj, dict) and obj.get("version") == INDEX_VERSION else None


def write_index(home: str, index: dict) -> None:
    write_json(paths.index_path(home), index)


def load_cache(home: str) -> dict:
    obj = read_json(paths.transcript_cache_path(home))
    if isinstance(obj, dict) and obj.get("version") == CACHE_VERSION and isinstance(obj.get("files"), dict):
        return obj["files"]
    return {}


def save_cache(home: str, files: dict) -> None:
    write_json(paths.transcript_cache_path(home), {"version": CACHE_VERSION, "files": files})


FOLDER_MEMORY_VERSION = 1


def load_folder_memory(home: str) -> dict[str, dict]:
    obj = read_json(paths.folder_memory_path(home))
    if isinstance(obj, dict) and obj.get("version") == FOLDER_MEMORY_VERSION and isinstance(obj.get("folders"), dict):
        return {k: v for k, v in obj["folders"].items() if isinstance(k, str) and isinstance(v, dict)}
    return {}


def save_folder_memory(home: str, folders: dict[str, dict]) -> None:
    write_json(paths.folder_memory_path(home), {"version": FOLDER_MEMORY_VERSION, "folders": folders})


def load_aliases(home: str) -> dict[str, str]:
    """{"/old/folder": "/new/folder"}: the user's answer for a folder Mishlat cannot find."""
    obj = read_json(paths.aliases_path(home), {})
    if not isinstance(obj, dict):
        return {}
    return {os.path.normpath(os.path.expanduser(k)): os.path.normpath(os.path.expanduser(v))
            for k, v in obj.items() if isinstance(k, str) and isinstance(v, str) and k and v}


def load_dismissed(home: str) -> dict[str, int]:
    obj = read_json(paths.dismissed_path(home), {})
    if not isinstance(obj, dict):
        return {}
    return {k: v for k, v in obj.items() if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)}


def dismiss(home: str, session_id: str, at: int) -> None:
    """Hide a session from the attention list until it has activity newer than `at`."""
    data = load_dismissed(home)
    data[session_id] = at
    write_json(paths.dismissed_path(home), data)


def load_assignments(home: str) -> dict[str, str]:
    """{session id: project folder}: the user's own choice, which wins over the automatic rule."""
    obj = read_json(paths.assignments_path(home), {})
    if not isinstance(obj, dict):
        return {}
    return {k: os.path.normpath(os.path.expanduser(v)) for k, v in obj.items()
            if isinstance(k, str) and isinstance(v, str) and v}


def assign(home: str, session_id: str, project_path: str | None) -> None:
    """Put a session under a project folder by hand; None gives it back to the automatic rule."""
    data = load_assignments(home)
    if project_path:
        data[session_id] = project_path
    else:
        data.pop(session_id, None)
    write_json(paths.assignments_path(home), data)


def load_descriptions(home: str) -> dict[str, str]:
    obj = read_json(paths.descriptions_path(home), {})
    if not isinstance(obj, dict):
        return {}
    return {os.path.normpath(os.path.expanduser(k)): v.strip() for k, v in obj.items()
            if isinstance(k, str) and isinstance(v, str) and v.strip()}


def describe(home: str, folder: str, purpose: str | None) -> None:
    """Set (or with None clear) the user's purpose line for a folder."""
    data = load_descriptions(home)
    key = os.path.normpath(os.path.expanduser(folder))
    if purpose and purpose.strip():
        data[key] = purpose.strip()
    else:
        data.pop(key, None)
    write_json(paths.descriptions_path(home), data)


def load_keep(home: str) -> dict[str, int]:
    """{session id: when the user said "השאר"}: never in the cleanup list."""
    obj = read_json(paths.keep_path(home), {})
    if not isinstance(obj, dict):
        return {}
    return {k: v for k, v in obj.items() if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)}


def keep(home: str, session_id: str, at: int) -> None:
    data = load_keep(home)
    data[session_id] = at
    write_json(paths.keep_path(home), data)


def unkeep(home: str, session_id: str) -> None:
    data = load_keep(home)
    if data.pop(session_id, None) is not None:
        write_json(paths.keep_path(home), data)


def load_delete_requests(home: str) -> dict[str, dict]:
    """{session id: {"title", "at"}}: approved for deletion, waiting for a Claude session to run it."""
    obj = read_json(paths.delete_requests_path(home), {})
    if not isinstance(obj, dict):
        return {}
    return {k: v for k, v in obj.items() if isinstance(k, str) and isinstance(v, dict)}


def request_delete(home: str, sessions: list[dict], at: int) -> None:
    data = load_delete_requests(home)
    for s in sessions:
        data[s["id"]] = {"title": s.get("title", ""), "cli_id": s.get("cli_id"), "at": at}
    write_json(paths.delete_requests_path(home), data)


def prune_delete_requests(home: str, existing_ids: set[str]) -> int:
    """Drop requests for sessions that are gone (deleted). Returns how many were dropped."""
    data = load_delete_requests(home)
    kept = {k: v for k, v in data.items() if k in existing_ids}
    if len(kept) != len(data):
        write_json(paths.delete_requests_path(home), kept)
    return len(data) - len(kept)


NOTIFY_MODES = ("others", "all", "off")  # others: every waiting session but the one the user looks at


def load_settings(home: str) -> dict:
    """{"roots": [...], "old_days": 30, "font_px": 15, "lang": "he", "notify": "others"}."""
    obj = read_json(paths.settings_path(home), {})
    obj = obj if isinstance(obj, dict) else {}
    roots = obj.get("roots")
    if isinstance(roots, list) and all(isinstance(r, str) for r in roots) and roots:
        roots = [os.path.normpath(os.path.expanduser(r)) for r in roots]
    else:
        roots = paths.default_roots(home)
    old_days = obj.get("old_days")
    if not isinstance(old_days, int) or isinstance(old_days, bool) or old_days < 1:
        old_days = OLD_DAYS
    font_px = obj.get("font_px")
    if not isinstance(font_px, int) or isinstance(font_px, bool) or not FONT_MIN <= font_px <= FONT_MAX:
        font_px = FONT_DEFAULT
    lang = obj.get("lang") if obj.get("lang") in LANGS else locale_lang()
    if os.environ.get("MISHLAT_LANG") in LANGS:  # a one-off override, for screenshots and trials
        lang = os.environ["MISHLAT_LANG"]
    notify = obj.get("notify") if obj.get("notify") in NOTIFY_MODES else NOTIFY_MODES[0]
    return {"roots": roots, "old_days": old_days, "font_px": font_px, "lang": lang, "notify": notify}


def save_setting(home: str, key: str, value) -> None:
    """Change one key of settings.json and keep the rest as the user wrote it."""
    obj = read_json(paths.settings_path(home), {})
    obj = obj if isinstance(obj, dict) else {}
    obj[key] = value
    write_json(paths.settings_path(home), obj)
