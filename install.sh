#!/usr/bin/env bash
# Install Mishlat for this user (Master laptop, no sudo). Run it again to upgrade.
#   MISHLAT_NO_RESTART=1     do not restart Nemo, the desktop icons or the tray
#   MISHLAT_NO_KEYBINDING=1  do not add the Super+Shift+C hotkey
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARE="$HOME/.local/share/mishlat"
BIN="$HOME/.local/bin/mishlat"
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"
NEMO_EXT="$HOME/.local/share/nemo-python/extensions"
NAUTILUS_EXT="$HOME/.local/share/nautilus-python/extensions"
KEY_ID="mishlat"
BINDING="<Super><Shift>c"
APP_ID="io.github.yosefco3.Mishlat"
DESKTOP="${XDG_CURRENT_DESKTOP:-}"

say() { printf '  %s\n' "$*"; }
running() {
  gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.NameHasOwner "$APP_ID" 2>/dev/null | grep -q true
}

echo "Installing Mishlat into $HOME"
mkdir -p "$SHARE/lib/mishlat" "$SHARE/icons" "$HOME/.local/bin" "$APPS" "$AUTOSTART"
rsync -a --delete --exclude '__pycache__' "$REPO/mishlat/" "$SHARE/lib/mishlat/"
say "package     $SHARE/lib/mishlat"
install -m 0644 "$REPO"/data/icons/*.svg "$SHARE/icons/"
say "icons       $SHARE/icons"
install -m 0755 "$REPO/bin/mishlat" "$BIN"
say "launcher    $BIN"
sed -e "s|@LAUNCHER@|$BIN|g" -e "s|@ICONS@|$SHARE/icons|g" "$REPO/data/mishlat.desktop.in" > "$APPS/mishlat.desktop"
say "menu entry  $APPS/mishlat.desktop"
sed -e "s|@LAUNCHER@|$BIN|g" -e "s|@ICONS@|$SHARE/icons|g" "$REPO/data/mishlat-autostart.desktop.in" \
  > "$AUTOSTART/mishlat.desktop"
say "autostart   $AUTOSTART/mishlat.desktop"
# The file-manager extension: Nemo (Linux Mint) always; Nautilus (GNOME) when it is installed.
rm -f "$NEMO_EXT/mishlat_nemo.py"   # the file's name before 2026-10-19
install -D -m 0644 "$REPO/extension/mishlat_fm.py" "$NEMO_EXT/mishlat_fm.py"
say "Nemo        $NEMO_EXT/mishlat_fm.py"
if command -v nautilus >/dev/null; then
  install -D -m 0644 "$REPO/extension/mishlat_fm.py" "$NAUTILUS_EXT/mishlat_fm.py"
  say "Nautilus    $NAUTILUS_EXT/mishlat_fm.py (written against nautilus-python 4; untested)"
fi

# The hotkey: Cinnamon and GNOME keep custom keybindings in gsettings, under different schemas.
add_key() {  # schema  path  list-key
  local schema="$1" path="$2" list_key="$3" current updated
  current="$(gsettings get "$schema" "$list_key")"
  updated="$(python3 - "$current" "$4" <<'PY'
import ast, sys
text, key = sys.argv[1], sys.argv[2]
items = ast.literal_eval(text.replace("@as ", "", 1)) or []
if key not in items:
    items.append(key)
print("[" + ", ".join(repr(i) for i in items) + "]")
PY
)"
  gsettings set "$schema.custom-keybinding:$path" name "Mishlat"
  gsettings set "$schema.custom-keybinding:$path" command "$BIN --toggle"
  gsettings set "$schema.custom-keybinding:$path" binding "${5:-['$BINDING']}"
  gsettings set "$schema" "$list_key" "$updated"
  say "hotkey      Super+Shift+C  ($updated)"
}
if [ "${MISHLAT_NO_KEYBINDING:-0}" != 1 ] && command -v gsettings >/dev/null; then
  case "$DESKTOP" in
    *Cinnamon*)
      add_key org.cinnamon.desktop.keybindings "/org/cinnamon/desktop/keybindings/custom-keybindings/$KEY_ID/" custom-list "$KEY_ID" ;;
    *GNOME*|*Unity*|*ubuntu*)
      p="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/$KEY_ID/"
      add_key org.gnome.settings-daemon.plugins.media-keys "$p" custom-keybindings "$p" "'$BINDING'" ;;
    *)
      say "hotkey      not set on '$DESKTOP': bind Super+Shift+C to '$BIN --toggle' in your desktop's keyboard settings" ;;
  esac
fi

if [ "${MISHLAT_NO_RESTART:-0}" != 1 ]; then
  if running; then "$BIN" --quit || true; sleep 1; fi
  command -v nemo >/dev/null && nemo -q >/dev/null 2>&1 || true
  command -v nautilus >/dev/null && nautilus -q >/dev/null 2>&1 || true
  if pgrep -x nemo-desktop >/dev/null; then
    pkill -x nemo-desktop || true
    sleep 1
    setsid nemo-desktop >/dev/null 2>&1 < /dev/null &
  fi
  setsid "$BIN" --tray >/dev/null 2>&1 < /dev/null &
  say "restarted   the file manager, the desktop icons and the Mishlat tray"
fi

echo "Done. Press Super+Shift+C, or run: mishlat"
