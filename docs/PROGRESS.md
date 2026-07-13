# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-13 (cont. 5) — Doc-interdependency review + a real feature/visual pass: Style archetype panel, percentile charts, Leaderboard colour

Opened the "bigger visual + docs pass" flagged at the end of the previous session with the doc
review first, as asked, then carried straight into app work rather than stopping to check back in
— per the open-ended framing ("scope isn't decided yet... open with that discussion"), reading all
docs surfaced concrete findings worth just fixing, and the app work followed the same "more than
visual — add real sections" brief.

**Doc review, all 16 `.md` files read end-to-end.** The cross-reference discipline holds up well
overall (the `metrics.json` doc-lint, `INITIATIVE.md` as the sole phase-table source, the
theory/tooling/decisions three-way split are all still clean) — four concrete things weren't:
(1) **`README.md` contradicted itself** — the live-demo link at the top implies a deployed, widened
app, but the body still said "not yet deployed" / "Premier League 2015/16 for v1" (both true before
2026-07-05/07-09, stale since). Rewritten with the real numbers (6 competitions, 1,635 players incl.
124 goalkeepers, live URL) and the repo-structure/Tech Stack sections updated (added `streamlit`,
pointed the `docs/` subtree at CLAUDE.md's index instead of hand-duplicating 3 of 12 files).
(2) **`CLAUDE.md`'s own Repository Layout omitted `docs/PRODUCT_SPEC.md`** despite it being actively
maintained and linked from three other docs — added. (3) **`ARCHITECTURE.md`'s Four Layers/Import
Graph never mentioned `app_data.py`** — the whole Phase 8 product-layer build step was invisible in
the one doc whose job is "how the pieces fit together"; added it as a third orchestration entry
point alongside `pipeline.py`/`manifest.py`/`metrics.py`, verified its actual imports via grep rather
than assumed. Also fixed a stale "future Streamlit app" phrase in the same file — it's deployed.
(4) **Two cross-doc line-number anchors (`MODULES.md#L57`, `MODULES.md#L53`) had already drifted to
the wrong section** (both pointed at Module B content instead of Module C — a real, demonstrable
consequence of using line anchors across files that get edited) — replaced all four markdown-to-
markdown line anchors repo-wide with heading anchors, which don't drift and (unlike `#Lxx`) actually
resolve in GitHub's normal rendered-markdown view, not just its blob/source view.

**App: two new features (not just visual), reusing existing computed data — no new modelling.**
Consulted the dataviz skill before writing chart code, per this project's own established habit;
manually verified the resulting orange/blue diverging pair against the dark panel surface (WCAG
contrast 4.89/3.23 respectively — Python computed, since `node` isn't installed here to run the
skill's own validator script) and confirmed against the skill's own anti-patterns doc that blue↔
orange is an explicitly endorsed diverging pair (blue↔aqua is the one it rejects, both cool).

- **New `plot_diverging_bar`** (`src/visualisation.py`) — one shared horizontal-bar function for
  "how does this compare to a baseline, direction and magnitude both matter" reads, parameterised by
  a reference value (50 for a percentile read, 0 for a z-score read) rather than two near-duplicate
  functions.
- **Style archetype panel** (Player explorer, outfield players only): `app_data.py` has computed a
  K=4 style-archetype `cluster` label per player since Phase 4, and `profile_clusters`
  (`src/similarity.py`) has existed since the notebooks needed it to name clusters ("ball-winning
  destroyer," etc.) — neither was ever surfaced in the live app. Now every outfield player's page
  shows *why* their cluster is what it is (top over/under-indexed stats as z-scores, plotted), plus
  a "Browse this archetype" expander listing other same-cluster players, clickable via the same
  jump-to-player mechanism the "players like X" table already uses. Goalkeepers skip this section —
  they aren't clustered yet (unchanged, known backlog item).
- **Percentile chart**: the "All per-90 stats" expander's plain sortable dataframe is now a
  percentile bar chart first (same diverging-bar function, reference=50), with the original
  dataframe kept as a nested "Table view" — matching the "every chart needs a table-view twin"
  convention `plot_similar_players_bar` already established.
- **Leaderboard**: G-xG now has a diverging background colour (orange over-performers, blue
  under-performers) via a pandas Styler + a small custom `LinearSegmentedColormap` blended through
  the dark panel colour, guarded on `notna().any()` so an all-blank filter (e.g. La Liga alone,
  outside Module A's flagship set) doesn't crash `background_gradient`'s vmin/vmax.

**A real, now-thoroughly-investigated open cosmetic bug, not fixed:** blank xG/G-xG cells render as
the literal text "None" (flagged as "candidate polish" back on 2026-07-08). Tried three independent
fixes this session (nullable `Float64` dtype, `Styler.format(na_rep=...)`, dropping
`column_config`'s own `format=`), each verified live against a freshly-restarted server — none
changed the "None" text, though the second attempt did confirm the Styler's format spec drives
*real*-value display. Conclusion: this Streamlit version's grid hardcodes missing numeric cells to
"None" regardless of Styler/column_config settings. Logged in full in
[ML_TOOLING.md](ML_TOOLING.md), including a false-start note (a plain browser reload doesn't
guarantee a dev server picked up an on-disk change — a full process restart does).

**Verification:** full `pytest` suite green throughout (**72**, unchanged — no `src/` logic
changed beyond the additive `plot_diverging_bar`, which isn't unit-tested, matching this codebase's
existing precedent of not testing plotting functions). A scripted `AppTest` pass covered all four
position groups plus all three views, zero exceptions. Playwright-over-Edge screenshots (system
Edge, per the established recipe) confirmed the new archetype panel, percentile chart, and Leaderboard
colour all render correctly across a defender, a goalkeeper (correctly skips the archetype section),
and the Leaderboard view.

**Backlog, deliberately not built this session (needs new model/code work first — logged, not
built):** goalkeeper clustering (style-archetype panel above is outfield-only until that lands),
cross-league similarity normalisation, a side-by-side two-player comparison view, market-value
integration (blocked on entity resolution, not data), a multi-season "player career" view (needs
new lineups pulls for the Barcelona seasons or similar). All pre-existing Phase 9/backlog items,
unchanged in scope by this session — no new backlog items were identified beyond what INITIATIVE.md/
ROADMAP.md/PITCH.md already tracked.

---

## Commit Status

Verified against `git log`/`git status` 2026-07-13. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit: `078caaf` ("Visual/brand pass: Leaderboard filters, Player explorer intro,
branding, About & Roadmap expansion"), pushed to `origin/main`. **Not yet committed as of this
write-up:** the doc-interdependency fixes and the Style archetype/percentile-chart/Leaderboard-
colour work in the "cont. 5" entry above — all verified (72 green, AppTest, Playwright screenshots)
but left uncommitted pending Guilherme's own review, per this project's "only commit when asked"
rule. Entries through 2026-07-13 (cont. 4) moved to [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md) to
keep this file under 150 lines.
