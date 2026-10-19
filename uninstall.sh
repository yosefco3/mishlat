#!/usr/bin/env bash
# Remove Mishlat for this user. Keeps ~/.cache/mishlat and ~/.config/mishlat unless --purge.
#   MISHLAT_NO_RESTART=1     do not restart the desktop icons
#   MISHLAT_NO_KEYBINDING=1  leave the hotkey alone (gsettings is not HOME-scoped: tests need this)
set -euo pipefail

SHARE="$HOME/.local/share/mishlat"
BIN="$HOME/.local/bin/mishlat"
KEY_ID="mishlat"
APP_ID="io.github.yosefco3.Mishlat"
DESKTOP="${XDG_CURRENT_DESKTOP:-}"

say() { printf '  %s\n' "$*"; }
remove() { if [ -e "$1" ] || [ -L "$1" ]; then rm -r -- "$1"; say "removed  $1"; fi; }

echo "Removing Mishlat from $HOME"
if gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
     --method org.freedesktop.DBus.NameHasOwner "$APP_ID" 2>/dev/null | grep -q true; then
  "$BIN" --quit || true
fi
remove "$BIN"
remove "$HOME/.local/share/applications/mishlat.desktop"
remove "$HOME/.config/autostart/mishlat.desktop"
remove "$HOME/.local/share/nemo-python/extensions/mishlat_fm.py"
remove "$HOME/.local/share/nautilus-python/extensions/mishlat_fm.py"
remove "$SHARE"
if [ "${1:-}" = "--purge" ]; then
  remove "$HOME/.cache/mishlat"
  remove "$HOME/.config/mishlat"
fi

drop_key() {  # schema  path  list-key  list-entry
  local schema="$1" path="$2" list_key="$3" entry="$4" current updated
  current="$(gsettings get "$schema" "$list_key")"
  updated="$(python3 - "$current" "$entry" <<'PY'
import ast, sys
text, key = sys.argv[1], sys.argv[2]
items = [i for i in (ast.literal_eval(text.replace("@as ", "", 1)) or []) if i != key]
print("[" + ", ".join(repr(i) for i in items) + "]")
PY
)"
  if [ "$updated" != "$current" ] && [ "$current" != "@as []" ]; then
    gsettings set "$schema" "$list_key" "$updated"
    gsettings reset-recursively "$schema.custom-keybinding:$path" || true
    say "hotkey removed"
  fi
}
if [ "${MISHLAT_NO_KEYBINDING:-0}" != 1 ] && command -v gsettings >/dev/null; then
  case "$DESKTOP" in
    *Cinnamon*) drop_key org.cinnamon.desktop.keybindings "/org/cinnamon/desktop/keybindings/custom-keybindings/$KEY_ID/" custom-list "$KEY_ID" ;;
    *GNOME*|*Unity*|*ubuntu*)
      p="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/$KEY_ID/"
      drop_key org.gnome.settings-daemon.plugins.media-keys "$p" custom-keybindings "$p" ;;
  esac
fi

if [ "${MISHLAT_NO_RESTART:-0}" != 1 ] && pgrep -x nemo-desktop >/dev/null; then
  pkill -x nemo-desktop || true
  sleep 1
  setsid nemo-desktop >/dev/null 2>&1 < /dev/null &
fi
echo "Done."
