# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-13 (cont. 3) — Goalkeepers wired into the app; Leaderboard copy expanded

Guilherme had a few hours left before the pitch and asked to attack the near-term backlog —
specifically anything that could visibly show up on screen, naming goalkeepers first — plus a
fuller Leaderboard description (it had 2-4 lines of small text) and a visual pass over every page,
backlog anything too big.

**Goalkeepers wired in, both layers.** `src/app_data.py` gained `_build_combined_gk_table`
(mirrors `_build_combined_similarity_table` but via `build_goalkeeper_per90_features`, same
`config.SIMILARITY_SETS` pool — no `config.py` change needed) and `build_app_artifacts` now
concatenates it onto the outfield table (`pd.concat` aligns columns automatically; outfield-only
columns are NaN on goalkeeper rows and vice versa). **124 goalkeepers** now in the pool (1,511 →
1,635 players total). `app.py` gained a 4th position-filter option, a `Goalkeeper` entry in
`SIGNATURE_STATS_BY_POSITION`, a `save_pct` caption where outfield players get the penalty
breakdown, and — the real restructuring — moved the `radar_axes` sidebar widget to render *after*
the player is picked (its options now depend on position group, which wasn't knowable at the old
call site) and introduced `position_feature_columns`/`position_action_columns` so the percentile
table, "All per-90 stats" expander, and `find_similar_players` call all branch correctly instead of
hardcoding the outfield columns. **Deliberately not clustered** — no K/silhouette decision made for
goalkeepers, so no style-archetype layer for them yet; "players like X" still works since
`find_similar_players` ranks by raw distance, not cluster membership.

**A real bug, caught by Streamlit's `AppTest` harness, not by reading the diff:**
`build_goalkeeper_per90_features` (written 2026-07-05) only returned `_p90` rate columns — unlike
the outfield builder, which always kept the raw season total *and* the rate. Invisible for over a
week because nothing had ever called it; the first goalkeeper pick in the app crashed with
`KeyError: 'saves'` in the signature-stats loop. Scripted `AppTest` against a real goalkeeper
selection (`position_filter=Goalkeeper` → pick the first match → check `.exception`) caught it in
seconds, far faster than a manual browser click-through would have. Fixed by adding
`GK_ACTION_COLUMNS` to the function's `keep_columns`, same pattern as the outfield builder — logged
in ML_LEARNING_LOG.md, since it's a data/feature-engineering gap, not a tooling one.

**Leaderboard page got a real description**, not just a caption: what the view is for (vs. the
Player explorer), a "what to look for" list per column (Goals vs. Non-pen goals, xG/G-xG, the new
Goalkeeper row's blank columns), replacing the previous 1-line caption.

**Full visual review, not just the goalkeeper path:** re-verified the Player explorer (a normal
outfield player, Harry Kane — zero regression from the radar-axes move), the Leaderboard (with the
Goalkeeper filter on), and the About & Roadmap tab (whole-number tiles auto-updated to 1,635
players) via Playwright-over-Edge. Nothing else needed fixing or backlogging this pass — the
Player explorer/Leaderboard/About & Roadmap trio already got a thorough pass earlier the same day.

**Self-inflicted hiccup, logged so it isn't repeated:** launched two overlapping
`python -m src.app_data` rebuilds without waiting for the first one to finish, which then
contended with each other for ~15 minutes before either produced output; killed both and ran one
clean invocation, which succeeded immediately after. Not an environment gotcha worth a
ML_TOOLING.md entry (self-inflicted by not waiting on the background task), but worth remembering:
wait for one rebuild to finish before starting another.

`config.py` untouched (reused `SIMILARITY_SETS` as-is); no new pytest tests added for the
`app_data.py`/`app.py` wiring itself, consistent with existing precedent (neither file has any test
coverage — `build_player_per90_features` itself is only exercised via monkeypatching in
`test_pipeline.py`, not a direct schema test). Full `pytest` suite re-run after the `similarity.py`
fix, still **72 green**.

---

## Commit Status

Verified against `git log`/`git status` 2026-07-13. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit: `5b8a27e` ("Pitch-prep: app About & Roadmap tab, whole-number headline
stats, doc-hygiene pass" — covers the earlier same-day work, now in
[PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)), pushed to `origin/main`. This session's changes
(goalkeepers wired into `app.py`/`src/app_data.py`, the `src/similarity.py` raw-totals fix, the
Leaderboard copy expansion, and doc updates across `MODULES.md`/`PRODUCT_SPEC.md`/`CLAUDE.md`/
`ML_LEARNING_LOG.md`/this file) are **not yet committed** — Guilherme to review before committing.
Entries through 2026-07-13 (cont. 2) moved to [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md) to keep
this file under 150 lines.
