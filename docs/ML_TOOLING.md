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

**Not every pull failure is transient — some are a real rate limit.** Attempting to pull Women's
EURO 2025 (Phase 4c, 2026-07-09) hit `429 Too Many Requests` from
`raw.githubusercontent.com` on the very first or second match every time, across several retries
spaced minutes apart over one session — unlike the single one-off `IncompleteRead` above, this
didn't clear with the existing "just retry, it's resumable" playbook. Likely a per-IP anonymous
rate limit on GitHub's raw-content host, not StatsBomb's data or our code. The resumable-cache
design still means a later retry (a different session, or after a longer cooldown) picks up
exactly where it left off at no extra cost — this just wasn't a same-session fix. Left genuinely
unwired rather than forcing it; see `INITIATIVE.md`'s Phase 4c log entry.

**Follow-up same session:** retried once more, hours later (per an explicit "retry but don't waste
time on it" ask). Still `429` — and this time the very first call, `sb.matches()` (the match-list
*metadata* request, not an event pull), was already rate-limited. That's a real escalation from the
first attempt (where at least a few events cached before the 429 hit each time): the limit isn't
scoped to the heavier per-match event endpoint specifically, it's blocking this IP against
`raw.githubusercontent.com` more broadly. Stopped after one attempt this time, as asked — did not
chain retries hunting for a window.

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

## A Playwright screenshot taken right after switching Streamlit views can show stale content

Symptom (2026-07-13, verifying `app.py`'s new "About & Roadmap" sidebar view): a screenshot taken
~2-3s after clicking a different `st.sidebar.radio` option showed the *new* view's content at the
top of the page, with the *previous* view's trailing elements (a shot map, an expander) still
rendered underneath — looked exactly like a real bug (two views bleeding into each other) on first
glance. It wasn't: re-shooting the same click with a longer wait (5-6s) came back clean every time,
from both a warm session and a fresh page load. Root cause: Streamlit only prunes DOM elements left
over from the previous script run once the *new* run fully finishes; a screenshot taken mid-run can
catch old trailing elements that haven't been removed yet, stacked below the new run's elements that
have already streamed in over the WebSocket. Same underlying mechanism as the "black screen" entry
below (content arrives incrementally, not atomically) — just the opposite failure mode (extra stale
content instead of none). **Lesson: if a click-driven Playwright screenshot shows something
inconsistent right after a rerun-triggering action (a view switch, a filter change), reshoot with a
longer wait before concluding it's a product bug** — this cost real back-and-forth twice in the same
session before the pattern was recognised.

## A local Streamlit "black screen" is almost always the WebSocket, not the app

Symptom (2026-07-08): `streamlit run app.py` opens a browser showing nothing but a black/empty
page. The app was **not** broken — the identical server rendered both views perfectly to headless
Edge via the Playwright recipe above. Streamlit delivers page content over a WebSocket *after* the
HTML `load` event, so if that socket never connects the dark page shell paints with no content — a
"black screen." Likely local causes and what to try, in order: hard-refresh to drop a stale cached
tab (Ctrl+Shift+R); confirm the `streamlit run` process is still alive and you opened the exact
`localhost:<port>` it printed (not an old tab on a dead port); try a different browser; temporarily
disable Avast's web shield (it already interferes with HTTPS/cert validation on this machine — see
the `certifi`/Playwright-download notes above — and can break localhost WebSocket upgrades too).
Diagnose, don't guess: drive the running server with the Playwright-over-Edge script and check
whether real content appears — if it does, the problem is the human's browser/network, not the code.

---

## A Playwright `get_by_text(..., exact=True)` can match more than one element as app copy grows

Symptom (2026-07-13, screenshotting the new sidebar branding): a verification script's
`page.get_by_text("About & Roadmap", exact=True).click()` — which had worked fine in earlier
sessions — started raising `strict mode violation: ... resolved to 2 elements`. Not a real app bug:
that same session's sidebar copy pass added a caption ("New here? Start with **About & Roadmap**
for the full story.") whose bold text is now an exact-text duplicate of the sidebar radio's own
"About & Roadmap" option label. Fix: scope the locator to the specific widget container instead of
searching the whole page — `page.get_by_test_id("stRadio").get_by_text("About & Roadmap",
exact=True)`. **Lesson: a bare `get_by_text(exact=True)` locator is only as stable as the app's copy
staying free of exact-text duplicates — as soon as this project's own habit of writing explanatory
captions/pointers ("see X for more") introduces a second copy of some label text, the same script
that worked last session can break. Prefer scoping to a `get_by_test_id(...)` container (e.g.
`stRadio`, `stSidebar`) over a bare page-wide `get_by_text` once an app has more than a couple of
short labels.**

## A missing value in `st.dataframe`'s `NumberColumn` renders as the literal text "None" — three independent fixes tried, none worked

Symptom (2026-07-13, Leaderboard's xG/G-xG columns — blank for ~2/3 of the pool outside Module A's
training set, by design, see PRODUCT_SPEC.md): every missing cell displays the literal text
`None`, not a blank cell, confirmed via a real screenshot rather than assumed from the code. Three
independent, real attempts to fix it, each verified live (fresh server restart + a new screenshot,
not just re-reading the diff — a stale-code false negative bit this same investigation once, see
below):

1. Cast the column to pandas' nullable `Float64` dtype (`pd.NA` instead of `np.nan`) — no change.
2. `Styler.format(..., na_rep="–")` — no change for missing values, **but this did confirm the
   Styler's format spec drives the display of *real* values** (`"{:+.1f}"` produced the `+4.2`-style
   strings seen in the screenshot) — so Styler formatting is read for populated cells, just
   overridden by a hardcoded "None" for missing ones.
3. Dropping `column_config.NumberColumn`'s own `format=` entirely (in case it, not the Styler, was
   forcing the literal) — no change.

**Conclusion: this Streamlit version's dataframe grid hardcodes missing numeric cells to "None"
ahead of any Styler-level `na_rep`, and no column_config option overrides it.** Left as a known,
now-thoroughly-investigated cosmetic gap rather than faked as fixed — `board.style.format(...,
na_rep="–")` is kept in `app.py` anyway since it correctly formats every real value, it just does
nothing for the missing ones.

**Self-inflicted false start along the way, worth flagging on its own:** the very first
verification (the `Float64` dtype attempt) looked unchanged after a plain browser `page.reload()`
against an already-running `streamlit run` dev server — but a *page* reload doesn't guarantee the
server picked up an on-disk code change; the fix might have silently still been running stale code.
Confirmed by fully killing and restarting the `streamlit run` process before each subsequent
screenshot, which is the only way to be certain a Playwright verification is exercising the current
file, not a cached script run from before the edit.

## How to use this file

- Hit a real environment/tooling obstacle this session (network, encoding, kernel, caching, a silent tool failure)? Add it here **before** the session ends, dated only if the fix might later change — most of these don't need a date, just the symptom and the fix. Don't wait for a retrospective "were there any obstacles?" question to write them down.
- Distinct from [ML_LEARNING_LOG.md](../ML_LEARNING_LOG.md): that file is *modelling* gotchas (a bug in feature engineering, a stats concept, a data-quality trap). This file is *environment/tooling* friction (Windows paths, encoding, kernels, network, background-task quirks) — a bug in `features.py` goes there even if the trigger was new data; a `curl` that silently fails goes here.
