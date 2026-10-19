# 02 — The state rules take the CLI status

## מטרה / Goal
`state_of` maps the listing's status; the row's question falls back to `waitingFor`. The scan
still passes the registry (next step wires the listing in).

## קבצים לשינוי / Files to change
- `mishlat/live.py` — `Live` gets `status: str | None = None`, `waiting_for: str | None = None`
  (the registry never fills them; the model reads one shape from both sources)
- `mishlat/model.py` — `state_of(..., live_status=None)`, `_session`
- `tests/test_model_index.py`

## מצב נוכחי / Current state
`model.state_of(status, fresh, alive, tx, now)`: working when alive and the transcript was
written in the last 90 s; then stopped, waiting (fresh blocked), review, open (alive), idle.
`_session` sets `question` to the store's needs_action / detail when the state is waiting.

## שינוי נדרש / Required change
### 1. `mishlat/model.py`
```python
def state_of(status, fresh, alive, tx, now, live_status=None):
    """working > stopped > waiting > review > open > idle. `live_status` is what
    `claude agents --json` says (busy / waiting / idle); without it a transcript write in the
    last 90 s means working."""
    if alive and (live_status == "busy" if live_status else
                  tx is not None and now - tx.get("last_write", 0) < WORKING_WINDOW_MS):
        return "working"
    ... stopped as before ...
    if (alive and live_status == "waiting") or (fresh and status == "blocked"):
        return "waiting"
    ... review, open/idle as before ...
```
`_session`: `live_status = live_entry.status if alive else None`; the question of a waiting row
is the store's needs_action / detail when its summary is fresh and blocked, else the CLI's
`waiting_for`; the row also carries `waiting_for` (raw) for the plugin.

## טסטים נדרשים / Tests required
- `state_of` table: busy → working even with an old transcript; idle → open even with a fresh
  write; waiting → waiting; waiting + fresh blocked → waiting with the store's question; idle +
  fresh blocked → waiting; idle + fresh review_ready → review; busy + fresh blocked → working;
  interrupted step + idle → stopped; no live_status keeps the 90 s rule; not alive → idle.
- `build_index` with `Live(..., status="waiting", waiting_for="permission prompt")` and no store
  question → `question == "permission prompt"`, `waiting_for` on the row, attention counted.

## קריטריון הצלחה / Success criteria
- All tests green; the index gains `waiting_for` on every session row (None unless waiting).

## קומיט / Commit
`feat(model): session state from the CLI's busy / waiting / idle`
