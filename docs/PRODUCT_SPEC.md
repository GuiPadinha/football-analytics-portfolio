# Product Layer — Interface Spec (Phase 8)

→ [CLAUDE.md](../CLAUDE.md) | Framing: [FRAMEWORK.md](FRAMEWORK.md) | Phase tracker: [INITIATIVE.md](INITIATIVE.md)

**Status:** spec expanded 2026-07-01; minimal v1 built 2026-07-04; two rounds of first-use
feedback on 2026-07-05 (see "Post-v1 additions" below) added real-time player search, per-position
"signature stats," a full per-90 stat table, a widened multi-competition player pool, a dark theme,
and defender-facing clearances/blocks stats; a 2026-07-06 fix-up pass corrected a real dark-theme
rendering bug (radar chart) and added whole-number season totals; a later 2026-07-06 pass shipped
the all-players **leaderboard** (goals incl. penalties + xG where available) — the first item off
the evening-feedback backlog below. Remaining backlog items (goalkeepers, clickable drill-down,
methodology-expander rework) are still open. Deployment to Streamlit Community Cloud is the one step
left for the maintainer to do (needs their account) — see the Build Checklist.

### Post-v1 additions (2026-07-05)

Guilherme's first real use of v1 surfaced three asks: real-time player search, more/better stats
per player, and a general "I expect a lot more, we'll iterate" expectation-setting.

- **Search:** the sidebar's two-step "position → player" flow became one global, prominent
  `st.selectbox` at the top of the main pane — Streamlit's selectbox already filters live as you
  type (a real combobox), so this needed no new dependency. Position is now an *optional* narrowing
  filter in the sidebar, not a prerequisite. (Superseded same day — see round 2 below: this still
  read as a dropdown-first interaction rather than a search box.)
- **Signature stats:** a `SIGNATURE_STATS_BY_POSITION` mapping in `app.py` surfaces 3 role-relevant
  per-90 metrics per position group (defender → tackles/interceptions/pressures, midfielder → key
  passes/progressive passes/pressures, forward → goals/shots/key passes) as headline metric cards,
  each with a percentile rank within the player's position group.
- **Full stat table:** an expander lists all 9 per-90 `ACTION_COLUMNS` with value + percentile,
  sortable — the "way more stats" ask, achievable entirely from data already in `app_data/`.
- **Named limitation, not silently skipped:** true SofaScore-depth stats (pass completion %, duels
  won %, aerial win %) need *new* features from raw StatsBomb events — rates need a denominator
  (attempts), and the current per-90 table only has completed-action counts. Flagged in the app's
  own "All per-90 stats" expander and here, not faked with the data we have today.

### Post-v1 additions, round 2 (2026-07-05)

A follow-up pass on the same day: round 1's selectbox-based search didn't read as "typing search,"
the player pool was locked to one 2015/16 league with no explanation of why, the app inherited
Streamlit's stock light theme, and assists/defensive-contribution stats were still buried in an
expander rather than surfaced.

- **Real typing search:** replaced the dropdown-first `st.selectbox` with an `st.text_input`
  ("Search for a player") that narrows a match list once committed (Enter or clicking away —
  `st.text_input` does not rerun per keystroke; corrected 2026-07-06 after actually driving the
  app with Playwright, see ML_TOOLING.md), feeding a selectbox of current matches with the top
  one pre-selected — the text
  box is now the obvious first thing to type into, not a combobox you click open before typing.
- **Widened player pool (Phase 4b real wiring):** the similarity pool now spans
  `config.SIMILARITY_SETS` — PL/La Liga/Serie A/Ligue 1 2015/16 plus Frauen Bundesliga/FA WSL
  2023/24 (6 competitions total), clustered together per position group, not per league. Named
  honestly in-app: StatsBomb's free data has no recent men's top-flight season at all (2015/16 is
  the ceiling for all four men's leagues here), so this is "wider," not "newer," for the men's
  side — the women's leagues are the newest full-season data anywhere in this project. No
  cross-league normalisation yet — flagged as a coarser signal in the "players like X" panel.
- **Dark theme:** `.streamlit/config.toml` repainted dark teal/gray with an orange primary accent;
  `app.py` mirrors the same palette in matplotlib rcParams (figure/axes backgrounds, text, grid,
  a custom orange/blue property cycle) so the charts match the surrounding chrome instead of
  rendering on a leftover white background. `plot_player_radar` gained optional dark-friendly
  colour parameters (default unchanged, so notebooks/pipeline PNGs are unaffected).
- **Assists + defender stats surfaced:** `assists_p90` promoted into the Midfielder/Forward
  signature stats (was already computed, just buried in the full-stat expander); new `clearances`
  and `blocks` action columns added to `ACTION_COLUMNS` for defender-facing "sofascore-like" stats
  — StatsBomb has no last-ditch/goal-line clearance sub-type, so a plain clearance count is the
  honest available proxy, stated as such in the app.
- **A real bug found along the way:** the pre-existing "zero completed passes" fallback in
  `extract_player_match_actions` produced a shapeless empty Series that could corrupt the whole
  function's output shape — surfaced by the new clearances/blocks test, not by production data
  (see ML_LEARNING_LOG.md). Fixed, not worked around.

### Backlog from 2026-07-06 feedback

Guilherme reviewed the round-2 build (actual screenshots, then live via Playwright — see
ML_TOOLING.md) and asked for the following; agreed to save it for a later session rather than
rush it in that night. **Items #1 and #2 shipped 2026-07-06 (cont. 2)** — see PROGRESS.md; the
rest are still open.

- **[DONE 2026-07-06] Full player leaderboard, sortable, goals *including* penalties + xG where
  available.** Built as a sidebar `View` toggle → sortable `st.dataframe` (`render_leaderboard` in
  `app.py`). The "goals incl. penalties" total is a new **display-only** `goals` column
  (`similarity.DISPLAY_COUNT_COLUMNS`, kept out of `ACTION_COLUMNS` so it never touches
  clustering/xG — exactly the "separate raw column, don't change the non-penalty modelling column"
  fix anticipated here). xG/`xg_diff` left-joined from the flagship table, **blank (not faked)** for
  players outside Module A's training set. Surfaces the intended outliers — e.g. Fabinho, a defender
  with 6 goals all penalties. (Was: "browse all players to spot outliers like Sergio Ramos's
  penalty-inflated total; needs a new multi-player table.")
- **"Under the hood (methodology)" flagged as low-value, under review.** Guilherme doesn't find it
  useful/understandable as-is; expects more charts to be added later that may reshape or replace
  it. Not touching it until there's a clearer idea of what replaces it — no redesign work now.
  → entry point: `app.py`'s `st.expander("Under the hood (methodology)")` (currently ~line 367).
- **Goalkeepers still not wired into the app** — `build_goalkeeper_per90_features` exists
  (`src/similarity.py:445`, verified still present 2026-07-09) but isn't in `config.py`/clustering/
  the app's position filter. Still an open integration decision (own K? own silhouette check? a 4th
  position-filter option alongside Defender/Midfielder/Forward?), now with an explicit ask to
  actually do it next session rather than leave it deferred indefinitely. Would touch: `config.py`
  (a GK dataset grouping), `src/app_data.py` (a 4th precomputed table or an extra column), `app.py`'s
  `SIGNATURE_STATS_BY_POSITION` + position filter + radar-axis choices (GK features are shots
  faced/saves/goals conceded/claims/punches/save_pct — none of the outfield `PER90_FEATURE_COLUMNS`
  apply, so several places assume exactly 3 groups and would need a look, not just a 4th dict key).
- **Clickable "similar player" names** — jump from the "players like X" list into that player's own
  page (and see *their* similar players — a recursive drill-down). *(No caveat after all — the
  earlier feedback message just got cut off mid-word; confirmed 2026-07-08 there was no unstated
  condition. Straightforwardly wanted, unblocked.)* → entry point: `app.py`'s `col_similar` block
  (currently ~lines 309–325) — the chart is a static `st.pyplot(plot_similar_players_bar(...))`,
  genuinely not clickable; the "Table view" `st.dataframe` just below it is the more promising path
  since Streamlit 1.58.0 (pinned in `requirements.txt`) supports
  `st.dataframe(..., on_select="rerun", selection_mode="single-row")` — a row click could set the
  picked-player state and rerun, without swapping chart libraries. Verified this is genuinely
  unbuilt: no `st.button`/`on_select` anywhere in `app.py` today.
- **Penalty info on the player page** (raised 2026-07-08). The single-player "Player explorer" page
  shows only `non_penalty_goals` (e.g. Zlatan reads "31") and nothing about penalties or total
  goals — so the page looks like it has *no* penalty data even though the leaderboard total includes
  them. The `goals` (incl. penalties) column already ships in `app_data/player_per90.parquet`
  (confirmed present 2026-07-09), so `penalties = goals - non_penalty_goals` is available with no
  data/rebuild work — this is a presentation-only add (e.g. a total-goals figure and/or a penalties
  count/split on the signature cards or the per-90 table). Small; the data's already there.
  → entry points: `SIGNATURE_STATS_BY_POSITION["Forward"]` uses `non_penalty_goals_p90`
  (`app.py:78`); the metric-card render loop that reads `player_row_full[raw_col]` is `app.py:258-267`
  — both `goals` and `non_penalty_goals` are already columns on `player_row_full`, no lookup needed.

---

## Purpose

Model output currently lives only inside notebooks: run cells, read tables — fine for building,
not for showing. [FRAMEWORK.md](FRAMEWORK.md) already names the fix (a single interactive screen)
and flags its absence as the main reason the project can currently feel abstract.

This layer turns a set of analyses into a tool: one shareable URL where an interviewer or a
football fan can click, pick a player, and immediately see the model's output. The screen stays
simple; the payoff is a genuine "players like X" ranking and a real over/under-performance number,
not UI chrome.

## Audience

Two audiences, one screen:
- **Interviewers / recruiters** — proof the models work end-to-end and that the author can
  ship a usable product, not just a notebook.
- **Football fans** — the "pick your favourite player, see who's like him" hook is
  self-explanatory and shareable.

Neither reads Python, so the screen has to explain itself.

---

## Screen Layout

Expanded from the [FRAMEWORK.md](FRAMEWORK.md#L103-L113) sketch. A left **sidebar** drives
selection; the **main pane** reacts live. Two lenses share the screen:

- **Similarity / scouting lens** (user input) — pick a player → radar vs. position peers +
  a ranked "players like X" list with distances.
- **xG / valuation lens** (no input) — that player's finishing over/under-performance, plus
  a shot map of where their chances came from.

```
┌───────────────┬─────────────────────────────────────────────────────────┐
│  SIDEBAR      │  Florian Wirtz   ·   Bayer Leverkusen   ·   Midfielder    │
│               │                                                           │
│  Competition ▾│  ┌────────────────────────┐  ┌─────────────────────────┐ │
│   Bundesliga  │  │  RADAR vs Midfielders   │  │  PLAYERS LIKE WIRTZ     │ │
│  Season      ▾│  │  [plot_player_radar]    │  │  1 Musiala    ####  0.41│ │
│   2023/24     │  │        _.-''-._         │  │  2 Odegaard   ###   0.58│ │
│  Position    ▾│  │      .'   ()   '.       │  │  3 Bellingham ##    0.73│ │
│   Midfielder  │  │     :     ##     :      │  │  4 Rogers     ##    0.79│ │
│  Player      ▾│  │      '._      _.'       │  │  5 Reijnders  #     0.88│ │
│   Wirtz       │  │         '-..-'          │  │  [find_similar_players] │ │
│               │  └────────────────────────┘  └─────────────────────────┘ │
│  Radar axes:  │  ┌──────────────────────────────────────────────────────┐│
│   [x] npxG    │  │  FINISHING — is the output real? [plot_player_xg_...] ││
│   [x] key pass│  │  Wirtz   +2.4 goals vs xG  #####  (over-performing)   ││
│   [x] prog pass  │  scored 12 · expected 9.6 · likely genuine, not noise ││
│   [ ] tackles │  └──────────────────────────────────────────────────────┘│
│   [ ] pressure│  ▸ Under the hood (calibration, silhouette, CV)  [expand] │
└───────────────┴─────────────────────────────────────────────────────────┘
```

### Interaction model

1. **Competition / Season** (sidebar dropdowns) — selects which precomputed dataset is
   loaded (see Data flow). Defaults to the flagship dataset (Leverkusen 2023/24).
2. **Position group** — Defender / Midfielder / Forward (GKs excluded, as in the models).
   Filters the player picker and sets the radar's peer comparison group.
3. **Player** — the one input that drives everything in the main pane.
4. **Radar axes** (multiselect) — the "customizable" knob: the user chooses which per-90
   metrics form the radar spokes, from `ACTION_COLUMNS`. This is the one live-recompute
   control that makes the screen feel dynamic without needing to re-run any model.
5. **Under the hood** (collapsed expander) — methodology plots for the technical
   interviewer; hidden by default so fans never hit a calibration curve.

---

## Component → Backend Map

Every panel is powered by a function that already exists and is unit-tested — the app is a
thin presentation shell over `src/`, reusing rather than reimplementing chart code.

| Screen panel                | Backend function (reuse as-is)                                        | File |
|-----------------------------|-----------------------------------------------------------------------|------|
| Player picker options       | `build_player_per90_features` (precomputed table)                     | [src/similarity.py](../src/similarity.py#L283) |
| Radar vs. peers             | `plot_player_radar`                                                    | [src/visualisation.py](../src/visualisation.py#L173) |
| "Players like X" ranking    | `find_similar_players`                                                 | [src/similarity.py](../src/similarity.py#L575) |
| Finishing over/under number | `build_player_xg_table` + `plot_player_xg_ranking`                     | [src/models.py](../src/models.py) · [src/visualisation.py](../src/visualisation.py#L58) |
| Per-player shot map         | `plot_shot_map`                                                        | [src/visualisation.py](../src/visualisation.py#L14) |
| (Optional) style-cluster map| `run_pca` + `plot_pca_clusters`                                        | [src/similarity.py](../src/similarity.py#L618) · [src/visualisation.py](../src/visualisation.py#L148) |
| "Under the hood" expander   | `plot_calibration_curve`, `plot_silhouette_curve`, `plot_elbow_curve` | [src/visualisation.py](../src/visualisation.py#L87) |

The diagnostic plots stay methodology evidence, not fan-facing — surfaced only in the
optional expander.

---

## Data flow

The app **reads precomputed artifacts, never pulls StatsBomb live.** Live pulls are slow
and rate-limited — unacceptable for a hosted demo that must respond to a click in under a
second. A build step (run locally, from the existing notebooks / `src`) writes flat tables
the app loads on startup and caches with `st.cache_data`.

Artifacts to precompute (one Parquet each, per competition/season):
- **Per-90 feature table** — `build_player_per90_features` output (drives picker + radar).
- **Player xG table** — `build_player_xg_table` output (drives the over/under panel).
- **Shot features** — `extract_shot_features` output + predicted xG (drives the shot map).

```
notebooks / src  ──build step──►  app_data/*.parquet  ──st.cache_data──►  Streamlit app
   (slow, offline)                (small, committed)       (instant)
```

**Open decision (flag at build time):** `data/` is gitignored, so a hosted demo needs its
artifacts shipped some other way — either a small committed `app_data/` folder (the per-90
and xG tables are tiny; the shot table is the only sizeable one) or Git LFS. Recommendation
leans committed `app_data/` for simplicity unless the shot table proves too large.

---

## Technology Choice (Streamlit)

**Chosen: Streamlit.** It fits the brief — "simple, but amazes because of the model output,
dynamic and customizable" — better than the alternatives considered below:

- Python-native: imports `src/similarity.py` and `src/visualisation.py` directly, zero
  rewrite of model logic. The reuse table above is literally the app.
- The player picker + live radar-axis recompute is Streamlit's exact sweet spot → the
  dynamic feel, with matplotlib figures from `visualisation.py` rendered as-is.
- Free hosting on Streamlit Community Cloud → one shareable URL for a CV / LinkedIn.
- Trade-off, stated honestly: the default look is a touch generic. Mitigated with a custom
  theme (`.streamlit/config.toml`) and team-colour accents — enough polish for a portfolio
  demo without a front-end rebuild.

**Considered and rejected:**
- **Plotly Dash** — more layout control and a more "custom web app" feel, but materially
  more code (callbacks, explicit layout) for a solo portfolio piece. Polish not worth the
  build cost here.
- **Static site + Plotly** — snappiest and most designed, but everything must be
  precomputed with no live recompute, which kills the customizable radar-axis interaction
  that makes the demo feel alive. Rejected on interactivity.

---

## Out of Scope (v1)

- No live model retraining or live StatsBomb pulls — precomputed artifacts only.
- No auth, no user accounts, no saved sessions.
- No 360-context xG or xGOT panels until Phase 7 lands (this spec targets the current
  pre-shot xG + similarity models).
- No SkillCorner physical panel — it shares zero players with the event data
  ([FRAMEWORK.md](FRAMEWORK.md) scope note), so it can't slot into a per-player screen.
  Could become a standalone "physical output" tab later; not v1.

---

## Build Checklist (Phase 8)

- [x] Add a `build step` (`src/app_data.py`, `python -m src.app_data`) that writes the three
      artifacts to `app_data/` for the flagship dataset (Premier League 2015/16).
- [x] Decide artifact shipping: **committed `app_data/`** — all three tables together are
      ~520KB, nowhere near needing Git LFS.
- [x] `app.py`: sidebar selectors → load cached artifacts (`st.cache_data`) → render the four
      panels via the reuse-map functions.
- [x] `.streamlit/config.toml`: theme (pitch-blue accent matching the radar chart's own colour).
- [x] Radar-axis multiselect wired to `feature_columns` of `plot_player_radar`.
- [x] "Under the hood" expander — reads `metrics.json` directly for the headline numbers, plus a
      live (cached) per-group silhouette curve; the full diagnostic-plot suite (calibration curve,
      elbow curve) stayed a v2 idea rather than shipping a fourth precomputed artifact for it.
- [x] Add `streamlit` to `requirements.txt` (pinned, `1.58.0`).
- [ ] **Deploy to Streamlit Community Cloud; put the URL in `README.md` and the portfolio** — the
      one step that needs the maintainer's own account, not something to automate.
- [x] Smoke test: verified headless via Streamlit's `AppTest` harness (no browser needed) — all 3
      position groups, 8 different players (including one with zero logged shots, to exercise the
      "no shot data" branch, and one with an accented name), and the zero-radar-axes edge case, all
      ran with zero exceptions.
- [x] Visually checked in a real browser (2026-07-08, Playwright-over-Edge screenshots) — both the
      Player explorer and the Leaderboard views render correctly (dark theme, dark radar chart,
      orange similar-players bars, sortable leaderboard). A locally-reported "black screen" was
      diagnosed as an environment/WebSocket issue on the maintainer's machine, not a code bug — see
      PROGRESS.md (2026-07-08) and ML_TOOLING.md.

---

## Additional Mockups

**Similarity lens close-up** — ranked neighbours with distance bars (shorter bar = closer):

```
PLAYERS LIKE FLORIAN WIRTZ  (Midfielders, per-90, standardised distance)
┌────────────────────────────────────────────────────────────┐
│  1  Jamal Musiala        (Bayern)      ####            0.41  │
│  2  Martin Odegaard      (Arsenal)     ######          0.58  │
│  3  Jude Bellingham      (Real Madrid) ########        0.73  │
│  4  Morgan Rogers        (Aston Villa) #########       0.79  │
│  5  Tijjani Reijnders    (Milan)       ###########     0.88  │
└────────────────────────────────────────────────────────────┘
   distance = Euclidean in standardised per-90 space, same group only
   [find_similar_players — src/similarity.py]
   (illustrative names/values — real output depends on the loaded dataset)
```

**xG lens close-up** — the over/under bar + shot map for the picked player:

```
FINISHING — real or variance?                    SHOT MAP  [plot_shot_map]
┌─────────────────────────────────┐   ┌───────────────────────────────────┐
│ scored        12                │   │            (goal)                  │
│ expected (xG)  9.6              │   │        o   ()   O                  │
│ difference    +2.4  #####       │   │      o    O  o     o    O = goal   │
│ read: over-performing —         │   │         o     o        o = miss    │
│ finishing above chance quality  │   │   o        o      o    size ~ xG   │
└─────────────────────────────────┘   └───────────────────────────────────┘
 [build_player_xg_table + plot_player_xg_ranking]      [plot_shot_map]
```

All mockups are ASCII wireframes — the real panels render the actual matplotlib /
mplsoccer figures from `visualisation.py`. Names and numbers here are illustrative.
