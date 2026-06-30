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

Fixed with `_safe_bool_column` / `_safe_column` helpers in `features.py` that substitute a default Series rather than assuming every match's schema is identical.
