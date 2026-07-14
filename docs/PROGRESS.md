# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-14 (cont.) — Search-box UX fix, Style archetype rework, percentile direction bug

Guilherme's ask: focus a pass on the webpages themselves — Style archetype "is boring and
confusing with that delta/beta (Greek letter)"; percentiles "not good at giving perception of
good/bad performance"; and "more real webpage behaviour in search boxes (inline suggestion/real
time suggestion) — try and 'play' with the webpage to see what I mean." App was already running
locally; used it directly (Playwright-over-Edge against the live `localhost:8501` server, not just
reading the code) to find and verify each issue before fixing it, per the "actually drive the app"
lesson ML_TOOLING.md already has on file from two earlier sessions.

**Search boxes.** Typing into the existing `st.text_input` + `st.selectbox` combo (Player explorer,
both Compare players pickers) produced no visible change until Enter/blur — confirmed live: typed
"mess" and the match count and dropdown both sat frozen on the old query. Replaced with a single
`st.selectbox` per search box (its dropdown already does instant client-side type-to-filter, no
server roundtrip) — same interaction as VS Code's Quick Open or GitHub's file finder. **This
revisits a shape PRODUCT_SPEC.md records as already tried and explicitly rejected once**
(2026-07-05 round 1: a bare selectbox "read as a dropdown-first interaction, not a search box,"
which is why round 2 built the text_input + selectbox combo this pass just removed) — flagged that
history to Guilherme directly rather than silently reverting it. Two things differ from round 1,
not just a straight revert: today's complaint was specifically about live-as-you-type behaviour,
which round 1 never had either (it was live-filtering but that wasn't the feedback that killed it);
and — the actual fix, confirmed with Guilherme via a direct question — every search box now starts
**blank** (`index=None`, placeholder text) instead of pre-filled with an already-selected player,
which round 1 always was. A pre-filled box reading as "a dropdown with a choice already made" is
plausibly a bigger part of the original "doesn't feel like a search box" complaint than the
click-to-focus mechanic itself, which is unavoidable with any combobox-shaped widget. Player
explorer's "About & Roadmap" copy and its own "How to use" steps updated to match (no more "press
Enter"). Leaderboard's name filter (feeds a multi-row table, not a single pick — no selectbox
pattern applies) kept as `text_input` but its placeholder now says "then press Enter" instead of
implying a live filter it can't deliver.

**Percentile direction bug.** Every percentile display in the app (signature stat cards, "All
per-90 stats" chart/table, Compare players table) computed `rank(pct=True)` directly on raw per-90
rates — correct for ten of eleven stats, backwards for the one where a *smaller* number is better:
a goalkeeper's `goals_conceded_p90`. A leaky keeper landed at the 90th+ percentile, reading as
"elite" next to every other percentile in the app. New `similarity.goodness_percentiles`
(+`LOWER_IS_BETTER_STATS`) flips just that column so every percentile means the same thing before
it's ever displayed — full account in ML_LEARNING_LOG.md. Also addressed the broader "percentile
alone doesn't convey good/bad" complaint: added `percentile_tier` (Elite/Very good/Good/Average/
Below average/Poor — the FBref/StatsBomb scouting-report convention) next to every percentile
number, everywhere one is shown. Found and fixed a smaller, pre-existing bug along the way while
touching every one of these format strings: percentiles read "91th" instead of "91st" (no ordinal
suffix logic) — new `format_percentile` helper fixes this app-wide.

**Style archetype rework.** Headline sentence dropped its inline "(+1.4σ)" parentheticals — "this
cluster does noticeably more X and less Y" now reads as plain English, with the exact z-scores one
click away in a new collapsed expander (mirrors the "All per-90 stats" expander's own progressive-
disclosure pattern, fixing the second complaint that the panel was "boring" — it no longer renders
a second full-height bar chart immediately under the first one). Inside that expander, bars are now
labelled "Much more (+1.4σ)" / "Typical (+0.1σ)" / "Somewhat less (-0.4σ)" via new
`style_intensity_label`, not a bare number — word first, Greek letter kept but demoted to a
secondary detail. Rounds before thresholding (not after) so two bars that display the same rounded
value never get different words.

**Verification.** Full `pytest` suite green (**89** — 86 unchanged + 3 new
`goodness_percentiles` cases in `test_similarity.py`). Playwright-over-Edge against a freshly
restarted local server (killed and relaunched twice mid-session to pick up on-disk changes, per
ML_TOOLING.md's "a page reload doesn't guarantee the server has the new code" lesson) confirmed:
live substring filtering with no Enter (typed "mess" → Messi appeared instantly at the top of the
dropdown); Player explorer and both Compare players pickers all start blank; the reworked Style
archetype panel renders plain-language labels with no visual duplication of the percentile chart
below it; percentile displays show tier words and correct ordinal suffixes (e.g. "91st (Very
good)"); a goalkeeper-relevant lower-is-better stat now reads consistently with every other stat.

**Docs updated:** PRODUCT_SPEC.md (this entry's search-box history cross-reference — full detail
lives here, not duplicated there), ML_LEARNING_LOG.md (the percentile-direction lesson, Module B).

---

## 2026-07-14 (cont. 2) — Scouting-report blurb + phase-alignment check-in

Two things this pass. First, a strategic check-in Guilherme raised directly: after several
sessions in a row inside Phase 8/9 (product/UX work), are Phases 5–7 (the core ML-depth phases —
xG uncertainty, Module B metric upgrades, 360-context xG) being quietly forgotten? Answered
honestly: yes, that's a real drift worth naming, not a false alarm — the Phase 8 order-jump on
2026-07-04 had a real deadline (a friend demo) that's since been satisfied, so continuing in Phase
9 no longer has that same justification. Recommended pivoting to Phase 5a (uncertainty on
goals−xG) next session. Before that, asked to rank the two open Phase 9 backlog items (the
Leaderboard filter question, the "new app features" candidates) by effort and do the fastest one
first — the **auto-generated scouting-report blurb** (reuses already-computed data, no new
modelling), clearly faster than a deep-link feature, a new team-level view, or the Leaderboard
filter's unresolved design question.

**Scouting-report blurb.** New `app.py` function `build_scouting_blurb` stitches three
already-rendered panels into one paragraph at the top of a player's page (new "Scouting report"
subheader, right after the page header): the Style archetype read (top 2 cluster traits + the
weakest one), the single best percentile stat (`percentiles.idxmax()`, using the same
goodness-adjusted percentiles and `percentile_tier` wording the rest of the page already uses),
and market value. A fixed template over already-verified numbers, not an LLM-generated summary —
it literally cannot say anything the rest of the page doesn't already say, since every value comes
from a computation that panel below it also uses. Required moving three existing computations
(`percentiles`, the cluster/`profile_clusters` read, the market-value lookup) earlier in the script
so the blurb has what it needs before its own panels render further down — reused, not duplicated;
the Style archetype and signature-stat sections below now read from the same already-computed
variables instead of recomputing them.

**Verification.** Full `pytest` suite green (**89**, unchanged — this is presentation-only, no
`src/` logic touched beyond the reordering, which changes nothing about what's computed). Playwright
-over-Edge confirmed the blurb reads sensibly for two different feature sets: a forward (Messi —
"A Key Passes and Progressive Passes forward, light on Clearances... Stands out most for Dribbles
Completed, ranking in the 100th percentile (Elite)... Valued at €120.0M") and a goalkeeper (Kasper
Schmeichel — confirms `goodness_percentiles`' goals-conceded flip doesn't surface a misleadingly
"good"-sounding stat via `idxmax()`). One honest nuance noted, not fixed: `idxmax()` can surface a
volume/context stat (e.g. a keeper's Shots Faced) as "stands out most for," which isn't really a
skill judgment the way Save % would be — inherited from the existing feature-set design (only
Goals Conceded is flagged direction-sensitive), not a new bug, and the same ambiguity already
exists in the percentile chart the blurb reads from.

**Docs updated:** ROADMAP.md (Phase 9 candidate list — scouting blurb marked done).

---

## Commit Status

Verified against `git log`/`git status` 2026-07-14. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit on `origin/main`: `78db78f` (search-box live-filtering fix, Style archetype
rework, percentile-direction bug fix). The scouting-report blurb entry above is **complete but not
yet committed** — working tree has uncommitted changes (`app.py`, `docs/ROADMAP.md`,
`docs/PROGRESS.md`) as of this write-up (per CLAUDE.md's Session Workflow, only commit when
explicitly asked).
