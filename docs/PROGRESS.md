# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-06 (cont.) — got real browser eyes on the app; new feedback logged as backlog, not built

Guilherme asked whether "Chrome headless + screenshots" (a technique a friend uses) makes sense
for Claude Code, since he suspected it might be terminal-only by design.

**It works, and it's now a documented capability.** Not a hard limitation — terminal access plus
an image-capable file-read tool is enough once something puts a real screenshot on disk. Getting
there took two wrong turns, both logged in [ML_TOOLING.md](ML_TOOLING.md): plain
`msedge --headless --screenshot` only ever captured Streamlit's loading skeleton (it waits for
the page `load` event, but Streamlit's content arrives after that, over a WebSocket); Playwright
fixed the waiting problem but its own browser download failed on this machine (Avast HTTPS
interception, the same class of issue as the earlier `certifi` gotcha) — worked around by pointing
Playwright at the already-installed Edge (`channel="msedge"`) instead of downloading one.

**Used it to actually verify the previous round's fixes** — confirmed via real screenshots (not
just re-reading the diff) that the radar chart's dark background genuinely renders now, signature
stats show whole numbers, and the "players like X" bar chart's colour ramp is correct (checked
actual pixel RGB values: closest match = full accent orange, fading toward the background for
farther matches).

**Found one real inaccuracy while poking at it further:** the app's search box does not rerun on
every keystroke the way earlier session comments/docs claimed — `st.text_input` needs Enter or a
blur to commit (it shows its own "Press Enter to apply" hint). Corrected the claim in `app.py`,
`docs/PRODUCT_SPEC.md`, and the placeholder text; left already-dated PROGRESS_ARCHIVE.md entries
alone (append-only history records what was believed at the time, same policy as the old 0.798
xG figure). The underlying UX (type a name, hit Enter, get filtered results) is unaffected — only
the "how it works" description was wrong, not the behaviour itself.

**New feedback captured as backlog, deliberately not built tonight** (Guilherme's own call —
"save all that for next session"): a sortable all-players leaderboard with goals *including*
penalties (so outliers like Sergio Ramos's penalty count show up) and visible xG where available;
the "Under the hood" methodology expander flagged as low-value/under review pending more charts;
goalkeepers still not wired into the app (feature engineering has existed since 2026-07-05); and
clickable "similar player" names for recursive drill-down (his message was cut off after "but" —
there was an unstated caveat, needs confirming before building). Full detail in
[PRODUCT_SPEC.md](PRODUCT_SPEC.md)'s new "Backlog from 2026-07-06 feedback" section.

Tests **65 green, unchanged** — only doc/comment accuracy fixes this pass, no behaviour change.

---

## 2026-07-06 — real screenshots surfaced a real bug: radar chart stayed white; whole-number totals added

Guilherme finally saw the round-2 theme pass running (screenshots) and the dark theme was broken
in one specific place — the radar chart — plus two functional asks: raw counting stats (not
per-90 decimals) as the headline numbers, and more visually engaging charts.

**Real bug, root-caused not patched around:** mplsoccer's `Radar.setup_axis()` defaults
`facecolor='#FFFFFF'` and calls `ax.set_facecolor()` itself *after* the axes already had the
correct dark background from rcParams — silently overwriting it. Every other chart (silhouette
curve, etc.) was already fine, which is what made this one white chart suspicious rather than "the
whole theme is broken." Fixed by threading `circle_facecolor` through to `setup_axis()` too.
Verified by actually rendering a synthetic radar and reading the saved PNG's pixel RGB values
(`#12181a` at the axes region) rather than re-reading the code and assuming.

**Whole-number totals:** `build_player_per90_features` now keeps raw `ACTION_COLUMNS` season
totals alongside the `_p90` rates (both in the same table — no separate rebuild path). Signature
stat cards now lead with the season total (e.g. "29" goals) with the per-90 rate + percentile
moved into the hover tooltip. Sanity-checked against reality: Cristiano Ronaldo's 2015/16 La Liga
non-penalty-goal total came out to 29 (real total was 35 incl. penalties) — checks out.

**A second real bug found while touching this table:** the "All per-90 stats" table sorted on a
pre-formatted percentile *string* ("98th"/"9th"), which sorts lexically wrong for single- vs
double-digit values. Fixed by sorting on the numeric percentile before formatting for display.

**More visual interest, per the dataviz skill:** invoked it before touching any chart/stat-tile
code. "Players like X" was a plain dataframe — converted to a horizontal bar chart
(`plot_similar_players_bar`, new in `visualisation.py`): one hue (the app's orange accent) with an
opacity ramp for closeness, direct distance labels at each bar's tip, recessive gridlines — the
skill's "compare magnitude → bar, sequential" form, not a categorical palette, since each row is
one entity's distance, not several parallel series. Kept the old dataframe as a "Table view"
expander underneath (the skill's "every chart needs a table-view twin" rule).

Tests **65 green, unchanged** (no new src logic needing a test — `plot_similar_players_bar`
follows the existing convention of not unit-testing plotting functions; `build_player_per90_features`'s
new raw columns are exercised by the full suite passing unchanged). `app_data/player_per90.parquet`
rebuilt (1,511 players, unchanged counts — just wider columns) and re-verified via the `AppTest`
headless smoke script.

**Answered, not yet actioned:** whether 2015/16 across the four men's leagues is "for
normalisation" — no, it's StatsBomb's actual data ceiling (that's the *only* full season available
for each), not a deliberate choice; and yes, real data is still on the table — the 16 Barcelona-only
La Liga seasons (2004/05–2020/21) are pulled (events) but not wired in (no lineups yet), which is
the direct lever for multi-season "career" depth already under discussion.

---

## Commit Status

Verified against `git log`/`git status` 2026-07-06. Committed through `428496f`:

- `25bbf79` — S6/7 — Radar charts + visuals + final polish + README
- `a3ff7cd` — Initiative Phases 0–1: framework charter, foundation hardening, data-integrity rebuild
- `bbc4ac8` — Phase 2 (Module A): xG ML-rigor (scaled logistic, CV, baseline ladder, calibrated GBM)
- `5e5aaef` — Phase 2 Module B rigor: silhouette score + minutes-weighted positions
- `4be7844` — Phase 5 (old numbering): expand product-layer interface spec + mockups (docs only)
- `e862a59` — Refactoring priorities and plan
- `6a1876c` — Phase 3 (spine A+B): CI workflow + data provenance manifest; config Phase 3→7 fix
- `102a134` — Phase 3 (spine 3b): metrics.json single source + doc-lint; docs reference it
- `ce45e74` — Phase 3 complete: headless pipeline.py + Makefile; add ARCHITECTURE.md; docs cleanup
- `0d4d2fe` — Phase 4 data expansion: config-driven datasets, sparse-column bug fix, obstacle docs
- `1c8d90d` — Model validation tests + Module A-B-C ordering pass + a real sparse-column fix
- `7f7a4e4` — Phase 8 minimal build: Streamlit app + build step, plus first-use fixes
- `29f753f` — Goalkeeper feature engineering (Module B) + 2026 World Cup backlog note
- `428496f` — Round-2 app UX pass: real typing search, dark theme, wider player pool, defensive stats

**Uncommitted as of this entry:** the 2026-07-06 fix-up pass — `app.py`, `src/similarity.py`,
`src/visualisation.py`, `app_data/player_per90.parquet`, `ML_LEARNING_LOG.md`, `docs/MODULES.md`,
`docs/ML_TOOLING.md`, `docs/PROGRESS.md`, `docs/PROGRESS_ARCHIVE.md` — ready to commit once
Guilherme gives the go-ahead (not yet asked for this round).
