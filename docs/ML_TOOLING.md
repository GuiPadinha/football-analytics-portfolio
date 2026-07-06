# Tooling / Environment Gotchas

Windows-specific friction hit while building this project. Written so they don't get silently re-solved every few sessions.

→ ML/stats decisions: [../ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md) | Theory: [ML_THEORY.md](ML_THEORY.md)

---

## Python / pip not recognized in a fresh terminal

Real Python 3.10 lives at `C:\Users\guilh\AppData\Local\Programs\Python\Python310\`. The Windows Store "App execution alias" stub can shadow it. Fix: call by full path when bare `python` fails:
```
& "C:\Users\guilh\AppData\Local\Programs\Python\Python310\python.exe" script.py
```
Original PATH fix in `docs/PROGRESS_ARCHIVE.md` (2026-06-28 entry) if this needs revisiting.

---

## UnicodeEncodeError with accented player names

PowerShell's default codepage is cp1252 — can't encode StatsBomb names (Kramarić, Šeško, Þór Sigurðsson, etc.). Fix before running any Python process that prints player names:
```powershell
chcp 65001                    # switch console to UTF-8
$env:PYTHONUTF8 = "1"        # before running Python
```
Or inside a script: `sys.stdout.reconfigure(encoding='utf-8')`.

---

## nbconvert corrupting accented names in notebook cells

Root cause: same cp1252 issue — the nbconvert subprocess inherits it. Fix: `$env:PYTHONUTF8 = "1"` in PowerShell before invoking `nbconvert`. Pass `--ExecutePreprocessor.kernel_name=fap310` to use the right kernel.

**StatsBomb quirk found at the same time:** Kanté is stored as `N''Golo Kanté` with a **doubled apostrophe** — not a typo here, genuine in the source data. Any future lookup by name needs the double apostrophe. Confirmed via `df[df['player'].str.contains('Kant')]` against the cached pickle.

---

## mplsoccer Radar raising `KeyError: 'bottom'`

Caused by passing `plt.subplots(subplot_kw={"polar": True})` to `Radar.setup_axis`. Radar expects a **plain rectangular `Axes`** and configures the polar-like projection internally — an already-polar axes breaks its spine-visibility logic (polar axes don't have `bottom`/`top`/`left`/`right` spines).

Fix: `fig, ax = plt.subplots()` with no `subplot_kw`, then `Radar.setup_axis(ax=ax)`.

General lesson: check a plotting library's expected input from its own examples/docstring, not from what the output visually looks like.

---

## VS Code Jupyter running on wrong interpreter (conda base 3.9)

Symptom: "Running cells with 'base (Python 3.9.12)' requires the ipykernel package" even with 3.10 pinned in `.vscode/settings.json`.

Root cause: Jupyter kernel is chosen separately from the Python interpreter. The `.ipynb` files had a `base` kernelspec baked into their metadata.

Two-part fix:
1. `jupyter.kernels.filter` in `.vscode/settings.json` to hide the conda-base interpreter
2. Normalize every notebook's `metadata.kernelspec` to the portable `python3`

For headless `nbconvert`: register the 3.10 env (`python -m ipykernel install --user --name fap310`) and pass `--ExecutePreprocessor.kernel_name=fap310`.

---

## Parquet vs. pickle for caching

**Flat tables** (processed shot tables, player per-90s) → Parquet: faster, portable, parquet-safe.

**Nested columns** (raw StatsBomb events with location lists, 360 freeze-frames) → Pickle: columnar Parquet can't round-trip nested list/dict columns.

Same project, two cache layers, two correct serialization choices — not a blanket "always use Parquet."

---

## StatsBomb sparse schema

StatsBombpy only includes a column in a match's events DataFrame if at least one event in that match uses it. So `pass_goal_assist` is absent entirely from matches with zero assists — a plain column access crashes.

Fixed with `safe_bool_column` / `safe_column` helpers in `data_loader.py` (shared by `features.py` and `similarity.py`) that substitute a default Series rather than assuming every match's schema is identical.

---

## Git Bash has no network egress; PowerShell does

Hit during Phase 4 research: `curl` and similar network calls from the Bash tool (Git Bash) silently return nothing in this environment, with no obvious error to explain why. PowerShell's `Invoke-WebRequest` works fine for the same request. Any raw HTTP fetch (verifying a StatsBomb competition/season id against the live API, checking a candidate data source) should go through PowerShell here, not Bash — don't burn time re-diagnosing a "network is down" false alarm.

---

## Background task stdout redirection hides output from the harness's own tracker

Redirecting a background command's stdout to a custom log file (`> pull.log 2>&1`) means the harness's own `.output` tracking file stays empty (0 lines) even though the process is running and producing output normally. Not a bug — the redirection just means the output never reaches the stream the harness tails. Check the custom log file directly (`Read`/`tail` on it) instead of assuming an empty `.output` means the process is stuck or silent.

---

## Transient network errors on large StatsBomb pulls

A multi-season/multi-competition bulk pull (Phase 4: 24 datasets, ~2,400 matches) hit one `IncompleteRead` connection error mid-download (Serie A 2015/16) — StatsBomb's open-data hosting occasionally drops a long-running connection with no pattern to it, not something our code did wrong. Fix isn't retry logic inside the pull itself; it's making the *orchestrating* script resumable: skip any dataset whose cache file already exists on disk, so a transient failure only costs re-running the whole script (one retry pass picks up exactly the datasets that didn't finish), not manual bookkeeping of what succeeded. See the Phase 4 pull script's file-exists check.

---

## Streamlit's first-run prompt blocks silently if nothing answers it

The very first time `streamlit run` executes on a machine, the CLI prints an interactive "Welcome
to Streamlit! ... Email:" prompt and waits for input *before* starting the server — no error, no
timeout, just silence in the terminal (and, from the running-it side, no browser tab ever opens,
because the server hasn't started). Pre-answer it once and it never asks again:

```bash
mkdir -p ~/.streamlit   # Windows: %USERPROFILE%\.streamlit
printf '[general]\nemail = ""\n' > ~/.streamlit/credentials.toml
```

## A committed `.streamlit/config.toml` with `[server] headless = true` breaks local dev

`headless` is meant for environments with no display (CI, a hosted deployment) — it stops
`streamlit run` from auto-opening a browser tab. Committing it in the *shared* `.streamlit/
config.toml` means every local `streamlit run app.py` inherits it too, so the app starts (server
comes up fine, `/_stcore/health` returns `ok`) but nothing visibly happens for someone just running
it locally — it looks identical to "the app crashed" from the user's side. Keep `[server]` out of
a committed config; let each environment (local vs. hosted) default appropriately on its own.

## A Streamlit selectbox whose `options` list changes needs a `key` tied to what changes it

`app.py`'s player search box is filtered by a position dropdown — when the position filter
changes, the player list changes underneath it. Without an explicit `key`, Streamlit tries to
carry the *previous* selection forward into the *new* options list; if that value isn't in the
new list, this raised a `KeyError` from deep inside Streamlit's session-state machinery (not a
clean, catchable error). Fix: key the dependent widget on the value that changes its options
(`key=f"player_search_{position_filter}"`) so it's treated as a fresh widget — starting over at
the first option — every time the filter changes, rather than trying to carry over a selection
that may no longer exist.

## Actually seeing the running Streamlit app (headless browser screenshots)

No screenshot tool is wired into this environment by default, but it's not a hard limitation —
terminal access (Bash/PowerShell) plus an image-capable Read tool is enough, if something can
actually put a real screenshot on disk. What worked, and what didn't:

- **`msedge.exe --headless --screenshot=out.png <url>` (old headless mode) doesn't work for
  Streamlit.** It kept capturing the loading skeleton, never the rendered app, regardless of
  `--virtual-time-budget` (tried up to 20000ms). Root cause: Streamlit's content arrives over a
  WebSocket *after* the page's `load` event, and old headless Chrome/Edge's `--screenshot` flag
  only waits for `load`; `--virtual-time-budget` manipulates JS timers in a way that doesn't play
  well with real-time WebSocket delivery anyway (a known class of issue with that flag).
- **Fix: Playwright, using the system-installed Edge instead of a downloaded browser.**
  `pip install playwright` works fine, but `playwright install chromium` fails on this machine
  with `UNABLE_TO_VERIFY_LEAF_SIGNATURE` (the same Avast HTTPS-interception issue as the earlier
  `certifi` gotcha — Node's own cert store doesn't trust Avast's root cert). Skip the download
  entirely: `p.chromium.launch(channel="msedge", headless=True)` drives the Edge that's already
  installed. Playwright's `page.wait_for_...` (e.g. waiting for real app text to appear) correctly
  waits for the WebSocket-delivered content, unlike the CLI screenshot flag.
- **`page.screenshot(full_page=True)` only captured the viewport**, not the whole scrollable page —
  Streamlit's main content sits in an inner scrollable container, not normal document flow, so
  Playwright's page-height detection doesn't see the extra content. Fix: just set a tall viewport
  (`viewport={"width": 1400, "height": 3000}`) instead of relying on `full_page`.
- Not added to `requirements.txt` — this is a local verification tool for actually looking at the
  app, not a runtime dependency of `app.py` itself.

---

## How to use this file

- Hit a real environment/tooling obstacle this session (network, encoding, kernel, caching, a silent tool failure)? Add it here **before** the session ends, dated only if the fix might later change — most of these don't need a date, just the symptom and the fix. Don't wait for a retrospective "were there any obstacles?" question to write them down.
- Distinct from [ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md): that file is *modelling* gotchas (a bug in feature engineering, a stats concept, a data-quality trap). This file is *environment/tooling* friction (Windows paths, encoding, kernels, network, background-task quirks) — a bug in `features.py` goes there even if the trigger was new data; a `curl` that silently fails goes here.
