# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-13 (cont. 6) — Goalkeeper clustering, cross-league similarity normalisation, and the Leaderboard "None" bug fixed

Three explicitly-scoped items from the top of this session, all shipped: goalkeeper style-archetype
clustering, cross-league normalisation for similarity (Phase 4b's original open item), and the
Leaderboard's long-standing blank-cell-shows-"None" cosmetic bug. Scoped before writing any code —
computed the real silhouette/elbow numbers on the actual production pools first (via scratch
scripts), rather than picking K or a normalisation design by assumption.

**Goalkeeper clustering.** No K-means/silhouette decision had ever been made for goalkeepers (wired
into the app 2026-07-05/07-13 with their own feature set, but "players like X" only ever ranked by
raw distance, no cluster label). Computed the elbow/silhouette curve on the actual 124-keeper
6-competition pool the app clusters (there's no single-league goalkeeper table to match the
outfield notebook's narrower scope against — goalkeepers only ever existed in the wide pool):
silhouette peaks at K=2 (~0.217, the same soft-continuum shape every outfield group shows). Kept
K=4 anyway, the same "archetype granularity over the metric's own preference" call already made for
outfield players, at a comparable silhouette value to theirs (0.155 vs. 0.133–0.153). Wired via a
new `src/app_data.py::_cluster_position_groups`, generalising the old outfield-only
`_add_cluster_labels` to take a group list and a feature-column list — goalkeepers and outfield
players now share one clustering code path and the app's Style archetype panel.

**Cross-league normalisation.** The similarity pool spans 6 competitions of very different
competitiveness (PL 2015/16 down to FA WSL 2023/24), and per-90 rates were being compared raw
across them. No external league-strength rating exists in this project's data (checked DATA.md's
SofaScore/FlashScore candidate-source note again — that's a standings-table source, not a
competitiveness index), so the honest, data-only fix is relative: `similarity.
normalize_within_competition` (new, `src/similarity.py`) expresses each per-90 stat as standard
deviations above/below the player's own competition's average before clustering or
`find_similar_players` ever compare across leagues. Checked whether this also changed the *K*
decision for the three existing outfield groups before shipping it — it didn't (silhouette still
peaks at K=2 for all three; K=4's value moves by ±0.02, not a material shift), which is the right
outcome: the fix should correct *which* players look similar, not accidentally retune how tightly
they cluster. Wired into `_cluster_position_groups` for both outfield and goalkeeper clustering, and
into `app.py`'s `find_similar_players`/cluster-profile calls via new `_lz`-suffixed feature-column
lists (`PER90_LEAGUE_Z_COLUMNS`/`GK_PER90_LEAGUE_Z_COLUMNS`). Radar axes, percentiles, and signature
stats deliberately stay on the raw per-90 rates — those are "how good is this player in real units"
displays, not a similarity computation, so a fan still reads an actual rate, not a z-score they'd
need to be taught to interpret. Copy updated throughout the app (Player explorer's "players like X"
caption, the Style archetype panel's explanatory text, "About & Roadmap"'s "How each model works"
and "What's already shipped, and what's next" sections, the Methodology expander's "Known
limitations" paragraph) to describe the real mechanism rather than the old "not yet designed"
language.

**Leaderboard "None" bug.** Three independent fixes were tried and verified live in the previous
session, none worked (full account in ML_TOOLING.md) — used `WebSearch` this time before attempting
a fourth blind fix, and found the real cause: a still-open Streamlit GitHub issue (#7360, "Allow
configuration of missing value placeholder in `st.dataframe`") confirms this Streamlit version
hardcodes a missing *numeric* cell to the literal text "None" with no config-level override —
consistent with why Styler `na_rep` and `column_config.NumberColumn`'s own `format=` both failed
regardless of how they were combined. The real fix has to happen at the data layer: `xG`/`G-xG` are
now hand-formatted `TextColumn`s (`f"{v:.1f}"`/`f"{v:+.1f}"`, `""` for missing) instead of
`NumberColumn`s, so there is no null numeric cell for the grid to special-case. The one
complication: G-xG's diverging background colour needs numeric input
(`Styler.background_gradient`), which can't run on the now-text column — worked around with a small
manual `_diverging_css` helper that samples the same colormap directly from the still-numeric
`xg_diff` values before they're overwritten by the display strings, applied via `Styler.apply`.
**Known, accepted trade-off, stated in a code comment:** these two columns now sort lexically when
a user clicks the header ("+10.5" sorts before "+4.2"), not numerically — there is no
`column_config` option in this Streamlit version to declare "sort by column A, display column B,"
so a perfectly numeric click-sort and a blank-for-missing cell aren't simultaneously achievable
here. The default row order (sorted by Goals) is unaffected.

**Verification.** Full `pytest` suite green (**75** — 72 unchanged + 3 new `test_similarity.py`
cases for `normalize_within_competition`: relative z-scoring across very different league
baselines, the zero-std/singleton-group guard, and grouping by an extra column). `python -m
src.metrics` regenerates `metrics.json` byte-identical (`git diff` empty) — this session's scope is
the app's wider multi-competition pool, not the notebook/pipeline's narrow single-competition one,
so the headline numbers every doc quotes are untouched by design. A scripted `AppTest` pass covered
all four position groups (including Goalkeeper, checking for the "Style archetype" subheader) and
all three views, plus the Leaderboard's all-blank-G-xG guard path (La Liga-only filter) — zero
exceptions. Playwright-over-Edge screenshots (system Edge, per the established recipe, at a wider
2000px viewport to fit every Leaderboard column) confirmed: zero literal "None" occurrences on the
Leaderboard with a La Liga-only filter (previously every blank cell in that view showed it); real
xG/G-xG values still render correctly with their diverging background colour intact; the goalkeeper
Style archetype panel renders a real 4-cluster readout ("skews high on Sweeper Actions... a style
shared with 33 other players") and a cross-league "players like X" match (an Italian Serie A
goalkeeper matched to a Premier League one).

**Docs updated:** MODULES.md (Module B's app-pool/goalkeeper/planned-upgrades paragraphs),
DATA.md (Phase 4 section), ML_LEARNING_LOG.md (two new dated Module B entries with the real
silhouette numbers behind both K decisions), ML_TOOLING.md (closed out the "None" bug entry with
the real fix and the GitHub issue reference), INITIATIVE.md (Log), ROADMAP.md (Phase 4b entry),
PITCH.md (open-backlog and "why isn't X done" sections), PRODUCT_SPEC.md (new dated section).

---

## Commit Status

Verified against `git log`/`git status` 2026-07-13. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit on `origin/main`: `5abd590`. The "cont. 6" entry above (goalkeeper
clustering, cross-league normalisation, Leaderboard "None" fix) is **complete but not yet
committed** — working tree has uncommitted changes as of this write-up (per CLAUDE.md's Session
Workflow, only commit when explicitly asked). Entries through 2026-07-13 (cont. 5) moved to
[PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md) to keep this file under 150 lines.
