"""Mishlat for the file manager: Claude marks on project folders, in Nemo (Linux Mint, also the
desktop icons) and in Nautilus (GNOME, nautilus-python 4.x; written against the API, untested).

Self-contained (copied to ~/.local/share/nemo-python/extensions/ and
~/.local/share/nautilus-python/extensions/). It only reads the index that the Mishlat tray writes
(~/.cache/mishlat/index.json) and adds:
  * an emblem on a folder with a session that waits for the user (or one that works now);
  * a "Claude" list-view column: sessions, attention ◐, working ●; a parent folder sums the
    projects under it;
  * two menu items: "שיחות Claude של התיקייה (N)…" and "סשן Claude חדש כאן".
"""

from __future__ import annotations

import json
import os
import subprocess

INDEX = os.path.expanduser("~/.cache/mishlat/index.json")
SETTINGS = os.path.expanduser("~/.config/mishlat/settings.json")
TEXT = {
    "he": {"projects": "{n} פרויקטים", "show": "שיחות Claude של התיקייה ({n})…", "new": "סשן Claude חדש כאן",
           "column": "Claude", "column_desc": "שיחות Claude בתיקייה (משלט)", "show_tip": "פותח את משלט על התיקייה הזו",
           "new_tip": "פותח שיחת Claude Code חדשה בתיקייה"},
    "en": {"projects": "{n} projects", "show": "Claude sessions of this folder ({n})…", "new": "New Claude session here",
           "column": "Claude", "column_desc": "Claude sessions in the folder (Mishlat)", "show_tip": "Opens Mishlat on this folder",
           "new_tip": "Starts a new Claude Code session in the folder"},
}


def ui_lang(settings_path: str = SETTINGS, environ=os.environ) -> str:
    """The language of the labels: settings.json "lang", else the locale."""
    try:
        with open(settings_path, encoding="utf-8") as f:
            lang = json.load(f).get("lang")
        if lang in TEXT:
            return lang
    except (OSError, ValueError, AttributeError):
        pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = environ.get(var) or ""
        if value:
            return "he" if value.lower().startswith("he") else "en"
    return "en"


def text(key: str, lang: str | None = None) -> str:
    return TEXT[lang or ui_lang()][key]
LAUNCHER = os.path.expanduser("~/.local/bin/mishlat")
EMBLEM_ATTENTION = "emblem-important"
EMBLEM_WORKING = "emblem-synchronizing"
REFRESH_S = 5
ATTRIBUTE = "mishlat_claude"
LRI, PDI = "⁦", "⁩"   # keep the digits in order inside a right-to-left column


class Mark:
    __slots__ = ("sessions", "attention", "working", "projects", "is_project", "lang")

    def __init__(self, is_project: bool, lang: str = "he") -> None:
        self.sessions = self.attention = self.working = self.projects = 0
        self.is_project = is_project
        self.lang = lang

    def add(self, project: dict) -> None:
        self.sessions += len(project.get("sessions") or [])
        self.attention += int(project.get("attention") or 0)
        self.working += int(project.get("working") or 0)
        self.projects += 1

    def label(self) -> str:
        parts = [str(self.sessions)]
        glyphs = " ".join(g for g in (f"◐{self.attention}" if self.attention else "",
                                      f"●{self.working}" if self.working else "") if g)
        if glyphs:
            parts.append(glyphs)
        text = LRI + " · ".join(parts) + PDI
        if self.projects > 1 or not self.is_project:
            text += " · " + TEXT[self.lang]["projects"].format(n=self.projects)
        return text

    def emblem(self) -> str | None:
        if self.attention:
            return EMBLEM_ATTENTION
        if self.working:
            return EMBLEM_WORKING
        return None

    def key(self) -> tuple:
        return (self.sessions, self.attention, self.working, self.projects)


def build_marks(index: dict, lang: str = "he") -> dict[str, Mark]:
    """path -> mark. A project folder gets its own; every folder between it and a root sums it.
    The roots (e.g. ~/Desktop) and folders outside them get no parent sums."""
    roots = [r.rstrip("/") for r in index.get("roots") or []]
    marks: dict[str, Mark] = {}
    for p in index.get("projects") or []:
        path = p.get("path")
        if not path or not p.get("sessions"):
            continue
        marks.setdefault(path, Mark(is_project=True, lang=lang)).add(p)
        parent = os.path.dirname(path)
        while any(parent.startswith(r + "/") for r in roots):
            marks.setdefault(parent, Mark(is_project=False, lang=lang)).add(p)
            parent = os.path.dirname(parent)
    return marks


class IndexCache:
    """The marks of the current index; re-read only when the file's mtime changes."""

    def __init__(self, path: str = INDEX) -> None:
        self.path = path
        self.mtime: float | None = None
        self.marks: dict[str, Mark] = {}

    def reload(self) -> set[str] | None:
        """The paths whose mark changed, or None when the index did not change."""
        try:
            mtime = os.stat(self.path).st_mtime
        except OSError:
            mtime = None
        if mtime == self.mtime:
            return None
        self.mtime = mtime
        new: dict[str, Mark] = {}
        if mtime is not None:
            try:
                with open(self.path, encoding="utf-8") as f:
                    new = build_marks(json.load(f), ui_lang())
            except (OSError, ValueError):
                new = self.marks  # a half-written file: keep the old marks
        changed = {p for p in set(new) | set(self.marks)
                   if (new[p].key() if p in new else None) != (self.marks[p].key() if p in self.marks else None)}
        self.marks = new
        return changed

    def get(self, path: str) -> Mark | None:
        return self.marks.get(path.rstrip("/") or "/")


def spawn(argv: list[str]) -> None:
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def menu_labels(mark: Mark | None, lang: str | None = None) -> tuple[str, str]:
    n = mark.sessions if mark else 0
    return text("show", lang).format(n=n), text("new", lang)


FM = None  # the file manager's extension module: Nemo or Nautilus
if not os.environ.get("MISHLAT_FM_NO_GI"):
    import gi
    for _name, _version in (("Nemo", "3.0"), ("Nautilus", "4.0"), ("Nautilus", "3.0")):
        try:
            gi.require_version(_name, _version)
            FM = getattr(__import__("gi.repository", fromlist=[_name]), _name)
            from gi.repository import GLib, GObject  # noqa: F811
            break
        except (ImportError, ValueError, AttributeError):
            FM = None

if FM is not None:
    _bases = [GObject.GObject, FM.InfoProvider, FM.ColumnProvider, FM.MenuProvider]
    if hasattr(FM, "NameAndDescProvider"):  # Nemo only
        _bases.append(FM.NameAndDescProvider)

    class MishlatNemo(*_bases):
        def __init__(self) -> None:
            GObject.Object.__init__(self)
            self.cache = IndexCache()
            self.cache.reload()
            self.files: dict = {}  # path -> the FileInfo the file manager showed, to refresh its mark
            GLib.timeout_add_seconds(REFRESH_S, self._refresh)

        @staticmethod
        def _path(file) -> str | None:
            if file.get_uri_scheme() != "file":
                return None
            loc = file.get_location()
            return loc.get_path() if loc is not None else None

        def update_file_info(self, file) -> None:  # called for every row Nemo draws: one dict lookup
            if not file.is_directory():
                return
            path = self._path(file)
            if not path:
                return
            mark = self.cache.get(path)
            if mark is None:
                file.add_string_attribute(ATTRIBUTE, "")
                return
            self.files[path] = file
            emblem = mark.emblem()
            if emblem:
                file.add_emblem(emblem)
            file.add_string_attribute(ATTRIBUTE, mark.label())

        def _refresh(self) -> bool:
            changed = self.cache.reload()
            for path in changed or ():
                f = self.files.get(path)
                if f is not None:
                    f.invalidate_extension_info()  # Nemo asks again, so the mark follows the state
            return True

        def get_columns(self):
            return (FM.Column(name="Mishlat::claude", attribute=ATTRIBUTE, label=text("column"),
                              description=text("column_desc")),)

        def _items(self, path: str):
            show_label, new_label = menu_labels(self.cache.get(path))
            show = FM.MenuItem(name="Mishlat::show", label=show_label, tip=text("show_tip"))
            show.connect("activate", lambda *_: spawn([LAUNCHER, "--project", path]))
            new = FM.MenuItem(name="Mishlat::new", label=new_label, tip=text("new_tip"))
            new.connect("activate", lambda *_: spawn(["claude-desktop", "--os-entry=folder_verb", path]))
            return [show, new]

        # Nemo and Nautilus 3 pass (window, files); Nautilus 4 passes (files): the last argument counts.
        def get_file_items(self, *args):
            files = args[-1]
            if len(files) != 1 or not files[0].is_directory():
                return []
            path = self._path(files[0])
            return self._items(path) if path else []

        def get_background_items(self, *args):
            path = self._path(args[-1])
            return self._items(path) if path else []

        def get_name_and_desc(self):
            return ["Mishlat:::Claude marks on project folders (reads ~/.cache/mishlat)"]
