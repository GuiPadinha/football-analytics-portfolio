# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-05 (cont.) — round 2 first-use feedback: real search, dark theme, defender stats, and Phase 4b actually wired in

Four asks in one message: the round-1 search still didn't read as "typing search," why the app is
locked to one 2015/16 league, a dark teal/gray + orange/blue theme, and assists/clearances still
not visible for a player.

**Real typing search:** swapped the round-1 `st.selectbox` for an `st.text_input` that narrows a
match list live on every keystroke, feeding a selectbox of current matches with the top one
pre-selected — the text box is now the obvious first thing to type into, not a dropdown you click
open before typing.

**Phase 4b actually wired in:** the app's player pool now spans `config.SIMILARITY_SETS` — PL/La
Liga/Serie A/Ligue 1 2015/16 + Frauen Bundesliga/FA WSL 2023/24 — **1,511 players** (up from 300),
clustered together per position group in `src/app_data.py`. Verified: typing "Kan" now surfaces
Kanté, Kane, Kankava, Kana-Biyik, Zukanović, Rytting-Kaneryd and Mbokani across 4 different
competitions in one search. Named the real ceiling explicitly rather than just widening quietly:
StatsBomb's free data has no recent men's top-flight season at all (2015/16 is the cap for all
four men's leagues here), so this is "wider," not "newer," for the men's side — the women's
leagues (2023/24) are the newest full-season data anywhere in this project. **No cross-league
normalisation yet** — flagged in the app's "players like X" panel and "Under the hood" expander as
a coarser signal than a same-league match, matching Phase 4b's original open item rather than
quietly resolving it.

**Dark theme:** `.streamlit/config.toml` repainted (`base="dark"`, orange primary, teal/gray
backgrounds); `app.py` mirrors the palette in matplotlib rcParams (figure/axes backgrounds, text,
grid, a custom orange/blue property cycle) so charts match the surrounding chrome. `plot_player_radar`
gained optional dark-friendly colour params (default unchanged — notebooks/pipeline PNGs unaffected).
**Not visually verified in a browser** — no screenshot tool available this session; verified via
Streamlit's headless `AppTest` harness only (script-level correctness). Asked Guilherme to eyeball
`streamlit run app.py` before calling the look done.

**Assists + defender stats:** `assists_p90` promoted into Midfielder/Forward signature stats (it
was already computed, just buried in the stat expander); new `clearances`/`blocks` action columns
(`ACTION_COLUMNS` 9→11) for Defender's signature stats. Checked StatsBomb's real `Clearance`/`Block`
event schema on cached data first — no goal-line-specific sub-type exists, so a plain clearance
count is the honest available proxy, stated as such in the app and MODULES.md.

**A real bug found along the way, not by production data:** the new clearances/blocks test exposed
that `extract_player_match_actions`'s zero-completed-passes fallback built a shapeless empty Series
(plain `RangeIndex` instead of the `(player, team)` `MultiIndex` every other action Series carries
even when empty) — corrupted `pd.concat`'s output shape whenever it was the only all-empty column.
Fixed by deriving the empty case the same way as everywhere else in the function. Unreachable with
real StatsBomb matches (always have passes), but a real landmine. See ML_LEARNING_LOG.md.

**Housekeeping:** regenerated `metrics.json` (silhouette shifted slightly for the new feature count,
e.g. defender 0.236→0.223 — same "soft continuum" finding, doc-lint test still green) and the
pipeline's cached per-90 pickle, so neither silently serves stale 9-column data. **Not done:**
re-executing notebook 03 — its saved cluster/neighbour tables were computed on 9 features and are
now a snapshot of the last real run, not current code; deferred rather than rushed, since the
clustering outcome could shift enough (which players land in which cluster) to need a careful
narrative re-check, not just a mechanical re-run.

Tests **61 → 65 green**. Full pytest suite + a headless `AppTest` smoke script covering typing
search, competition filter, and all 3 position groups, all green.

**Also raised, not yet addressed:** wanting all La Liga data available (not just the one full
season — the 16 Barcelona-only seasons are pulled but not wired in) and a new "player career" page
with multi-season drill-down + international-tournament stats + trophies/individual awards/MOTMs.
The last part doesn't exist in any current data source (StatsBomb has no honours/awards data at
all) — scoping this with Guilherme rather than guessing at it.

---

## 2026-07-05 (cont.) — goalkeeper feature engineering + a World Cup 2026 backlog note

Two asks that arrived mid-session: add goalkeepers to Module B, and note a 2026 World Cup
predictive-model idea for later.

**Goalkeepers:** investigated StatsBomb's `Goal Keeper` event schema on real cached data before
writing anything (`goalkeeper_type` values across 15 matches: Shot Faced, Shot Saved [+3 rarer
synonyms], Goal Conceded, Collected, Punch, Keeper Sweeper). New `extract_goalkeeper_match_actions`
+ `build_goalkeeper_per90_features` (`src/similarity.py`) give keepers their own feature set —
shots faced, saves, goals conceded, claims, punches, sweeper actions per 90, plus `save_pct` — kept
deliberately separate from the outfield `ACTION_COLUMNS` rather than a branch inside the same
function (a keeper's tackle/pass-progression rate is meaningless; same "cluster per position
group" lesson as S6, one step further). Refactored the shared match-iteration loop out of
`build_player_per90_features` into `_build_season_minutes_and_actions` so both builders reuse it —
verified byte-identical output for the existing outfield function before trusting the refactor.
+2 tests (`test_similarity.py`). Verified on real PL 2015/16 data: 27 keepers clear the 900-minute
floor, recognisable names (Čech, de Gea, Lloris, Courtois, Schmeichel). One honest caveat found by
actually looking at the numbers: `save_pct` (25-51%) reads lower than the broadcast "save %" stat
(usually 65-75%) — likely because StatsBomb's `Shot Faced` count isn't restricted to shots on
target. Documented in MODULES.md rather than hidden or asserted-correct without checking.

**Not done in this pass, on purpose:** wiring goalkeepers into `config.py`, clustering (own K?),
or the app's position filter — a separate integration decision, not rushed into the same pass as
the feature engineering.

**World Cup 2026 note:** added to ROADMAP.md/INITIATIVE.md's Phase 9 backlog — flagged that the
first step has to be checking whether StatsBomb has released *any* open data for it yet, since
every tournament this project already uses was released after the tournament ended, not live, and
the 2026 World Cup may still be running. Scope (target, features, train set) deliberately left
undefined until that's checked.

Tests **59 → 61 green**. `src/similarity.py` + `tests/test_similarity.py` changed; docs updated
(MODULES.md, ML_LEARNING_LOG.md, ROADMAP.md, INITIATIVE.md, CLAUDE.md test count).

---

## Commit Status

Verified against `git log`/`git status` 2026-07-05. Committed through `29f753f`:

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

**Uncommitted as of this entry:** today's round-2 UX/data pass — `app.py`, `src/app_data.py`,
`src/config.py`, `src/similarity.py`, `src/visualisation.py`, `.streamlit/config.toml`,
`app_data/player_per90.parquet`, `metrics.json`, `tests/test_similarity.py`, and docs
(`CLAUDE.md`, `ML_LEARNING_LOG.md`, `docs/INITIATIVE.md`, `docs/MODULES.md`, `docs/ROADMAP.md`,
`docs/PRODUCT_SPEC.md`, `docs/PROGRESS.md`, `docs/PROGRESS_ARCHIVE.md`) — ready to commit once
Guilherme gives the go-ahead (not yet asked for this round).
