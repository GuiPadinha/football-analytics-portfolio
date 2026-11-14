# Tooling gotchas: archive

Moved out of [ML_TOOLING.md](ML_TOOLING.md) on 2026-11-14: the tool is gone (Playwright, matplotlib in the app,
conda) or the fix was one-off. Kept for history.

---

## A leftover `.git` folder on Google Drive that cannot be deleted (2026-10-17)

After deleting an old copy of this repo from `OneDrive ISCTE (arquivo)` on the Drive, one empty
`.git` folder stayed behind. `Remove-Item -Recurse -Force`, `rmdir /s /q` and Explorer all failed
with "Access is denied", and even `Get-Item` on it failed, although `icacls` on the parent showed
full control. The copy's git was already corrupted (`bad object HEAD`). **Fix:** trash the parent
folder through the Drive API (the Drive connector's `trash_file`; "Move to trash" in the Drive web
UI does the same). It disappeared locally within seconds and stays in the Drive trash for 30 days.
`takeown`/`icacls` were not tried. Lesson: delete old repo copies in Drive in one go, or leave them
alone, since a half-deleted `.git` on the mount can get stuck.

## VS Code Jupyter running on wrong interpreter (conda base 3.9)

Symptom: "Running cells with 'base (Python 3.9.12)' requires the ipykernel package" even with 3.10 pinned in `.vscode/settings.json`.

Root cause: Jupyter kernel is chosen separately from the Python interpreter. The `.ipynb` files had a `base` kernelspec baked into their metadata.

Two-part fix:
1. `jupyter.kernels.filter` in `.vscode/settings.json` to hide the conda-base interpreter (that file is local-only since 2026-10-02: it holds machine-specific paths, so it is gitignored)
2. Normalize every notebook's `metadata.kernelspec` to the portable `python3`

For headless `nbconvert`: register the env (`python -m ipykernel install --user --name fap312` — 3.12, registered 2026-10-02; the older `fap310` kernel still exists) and pass `--ExecutePreprocessor.kernel_name=fap310`.

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

## Streamlit Cloud app crashes on `import matplotlib`: the package install failed

Hit 2026-10-03 on the redeploy. The new app showed `ModuleNotFoundError` at `app.py`'s first
third-party import (`matplotlib`). Streamlit and its own dependencies (pandas, numpy, pyarrow)
come pre-installed, so when installing `requirements.txt` fails, the app still starts, with only
those. The cause: the deploy form's Python had been left on the Cloud default, 3.14, and the pinned
numpy 2.2.6 has no 3.14 wheel, so the whole install failed. Fix chosen: bump numpy to 2.3.5,
the oldest line with 3.14 wheels, rather than redeploy on 3.12. Before pinning, check that every
runtime package has a wheel for the Cloud's Python (PyPI's JSON API lists them:
`https://pypi.org/pypi/<package>/<version>/json`). The first lines of the app's log ("Manage
app") show the Python version and the failed install. Another trap from the same deploy: leaving
"App URL" blank gives a random subdomain, and the old link 404s until the subdomain is set in the
app's settings.

