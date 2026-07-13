# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-13 (cont. 4) — Visual/brand pass: Leaderboard filters, Player explorer intro, brand identity, About & Roadmap expansion

Same-day follow-up after the goalkeeper wiring below. Guilherme asked for four things: filter the
Leaderboard by name/position, improve the Player explorer page's intro, make the sidebar/page
headers more visually developed with an appealing icon/brand/slogan, and expand About & Roadmap
with the data used, the methods, and where the models are headed next.

**Leaderboard filters.** `render_leaderboard` (`app.py`) gained an in-page name search
(`st.text_input`) and a position `st.multiselect` (defaulting to all options) above the table —
additive to the sidebar's shared position/competition filters, not a replacement, since the
sidebar narrows the whole pool (shared with Player explorer) while these two are scoped to
Leaderboard browsing itself. Empty-selection and no-match states both handled (a warning, not a
crash).

**Player explorer intro.** The page previously opened straight into a bare search box with no
title or explanation at all. Now opens with a proper header + a short markdown paragraph naming
every panel on the page (signature stats, radar, "players like X," Finishing).

**Brand identity.** New `BRAND_ICON = "⚽"` / `SLOGAN = "Scout by data, not by reputation."`
constants, threaded through: the browser tab (`st.set_page_config(page_icon=...)`), a new
`render_page_header()` helper (title on the left, a small icon+slogan badge in the top-right —
used by the Leaderboard, Player explorer, and every per-player page), and a rebuilt sidebar (brand
header, two live `st.metric` quick-facts — Players, Competitions — computed from `per90`, not
hardcoded, a "New here? Start with About & Roadmap" pointer, and a GitHub source link).

**About & Roadmap expansion.** Two new always-visible sections: "Data used" (the actual
competitions/seasons feeding each model — similarity pool, xG training set, the 4 generalisation
tournaments, SkillCorner) and "How each model works" (plain-language K-means/Euclidean-distance/PCA
for similarity, logistic regression for xG). Both are prose/dataset-name content with no bare
decimals, so they don't collide with the whole-number-headline rule the "Methodology" expander
already follows (see the 2026-07-13 cont. 2 entry in PROGRESS_ARCHIVE.md for that rule's origin).
The "what's next" roadmap paragraph also grew a third tier, "**A third lens, not started**,"
naming Module C (Performance Under Pressure) explicitly — it hadn't appeared anywhere in the app
before this pass, only in MODULES.md/ROADMAP.md.

**Verification:** a scripted `AppTest` pass over all three views plus both new Leaderboard filters
and a goalkeeper pick came back with no exceptions; Playwright-over-Edge screenshots of all three
pages confirmed the visual result matches intent (brand badge top-right of every header, sidebar
quick-facts, filters both populated and functional). Full `pytest` suite re-run, still **72
green** (no `src/` changes this pass, `app.py`-only).

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
status`. Latest commit: `919b6ce` ("Wire goalkeepers into the app; expand Leaderboard copy" —
covers the goalkeeper-wiring session above, now the "cont. 3" entry), pushed to `origin/main`.
This session's changes (the visual/brand pass above — Leaderboard filters, Player explorer intro,
`render_page_header`/sidebar branding, the About & Roadmap data/methods/roadmap expansion — plus
doc updates to this file and `PRODUCT_SPEC.md`) are **not yet committed** — Guilherme to review
before committing. Entries through 2026-07-13 (cont. 2) moved to
[PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md) to keep this file under 150 lines.
