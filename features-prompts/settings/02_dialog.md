# 02 — The settings dialog

## מטרה / Goal
A dialog in the window to change the two settings: notifications (others / all / off) and the
old-days threshold. Opened from a ⚙ header button or Ctrl+,. Saves through `io.save_setting`
and requests a scan.

## קבצים לשינוי / Files to change
- `mishlat/window.py` — `_settings()` dialog, `apply_settings(values)`, header button, Ctrl+,.
- `mishlat/strings.py` — English for the new strings.
- `tests/test_window_smoke.py` — `apply_settings` writes both keys and asks for a scan.

## מצב נוכחי / Current state
The header (window.py 160-168) has one button (rescan). Dialogs follow `_describe` (660-690):
`Gtk.Dialog` with Cancel / Save, `run()`, read the widgets, `destroy()`. `_on_key` (584-612)
handles Ctrl+F/R/+/-/0/L and Escape.

## שינוי נדרש / Required change
1. `window.py`: `NOTIFY_CHOICES = (("others", "על כל שיחה שמחכה לך, חוץ מזו שאתה בה"), ("all", "על כל שיחה שמחכה לך"), ("off", "כבויות"))`.
   `_settings()`: a `Gtk.ComboBoxText` over the choices (active = saved value) and a
   `Gtk.SpinButton` 1–365 (value = saved old_days); on OK → `apply_settings({"notify": …, "old_days": …})`.
   `apply_settings(values)`: `io.save_setting` for each key whose value changed, then `_request_scan()`.
   A `Gtk.Button` "emblem-system-symbolic" in the header (tooltip "הגדרות (Ctrl+,)") and `Gdk.KEY_comma` in `_on_key`.
2. `strings.py`: EN entries for the title, labels, choices and tooltip.

## טסטים נדרשים / Tests required
- `apply_settings({"notify": "off", "old_days": 7})` on a fake home ⇒ settings.json holds both; a fake app records one scan request.
- `t()` of every new string differs from the Hebrew when the language is `en`.

## קריטריון הצלחה / Success criteria
- Ctrl+, opens the dialog; Save changes settings.json and the next scan uses the values.
- All existing tests still pass.

## קומיט / Commit
`feat(window): a settings dialog for notifications and the old-days threshold`
