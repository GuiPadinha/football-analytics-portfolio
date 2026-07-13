# Product Layer — Interface Spec (Phase 8)

→ [CLAUDE.md](../CLAUDE.md) | Framing: [FRAMEWORK.md](FRAMEWORK.md) | Phase tracker: [INITIATIVE.md](INITIATIVE.md)

**Status:** spec expanded 2026-07-01; minimal v1 built 2026-07-04; two rounds of first-use
feedback on 2026-07-05 (see "Post-v1 additions" below) added real-time player search, per-position
"signature stats," a full per-90 stat table, a widened multi-competition player pool, a dark theme,
and defender-facing clearances/blocks stats; a 2026-07-06 fix-up pass corrected a real dark-theme
rendering bug (radar chart) and added whole-number season totals; a later 2026-07-06 pass shipped
the all-players **leaderboard** (goals incl. penalties + xG where available) — the first item off
the evening-feedback backlog below. **Deployed to Streamlit Community Cloud 2026-07-09** —
[gpfootball-analytics-portfolio.streamlit.app](https://gpfootball-analytics-portfolio.streamlit.app)
(Python 3.10 pinned in the deploy settings, see ROADMAP.md's Phase 9 backlog note). Phase 8 is now
fully done; the remaining backlog items (goalkeepers, clickable drill-down, methodology-expander
rework, penalty info) below are app-polish, not Phase 8 build items.

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
rush it in that night. **All five items below are now done** (last one, goalkeepers, shipped
2026-07-13) — the only thing still open from this whole list is the minor cosmetic follow-up
noted inside the drill-down item below (an expander's open/closed state not always carrying over
across a jump).

- **[DONE 2026-07-06] Full player leaderboard, sortable, goals *including* penalties + xG where
  available.** Built as a sidebar `View` toggle → sortable `st.dataframe` (`render_leaderboard` in
  `app.py`). The "goals incl. penalties" total is a new **display-only** `goals` column
  (`similarity.DISPLAY_COUNT_COLUMNS`, kept out of `ACTION_COLUMNS` so it never touches
  clustering/xG — exactly the "separate raw column, don't change the non-penalty modelling column"
  fix anticipated here). xG/`xg_diff` left-joined from the flagship table, **blank (not faked)** for
  players outside Module A's training set. Surfaces the intended outliers — e.g. Fabinho, a defender
  with 6 goals all penalties. (Was: "browse all players to spot outliers like Sergio Ramos's
  penalty-inflated total; needs a new multi-player table.")
- **[DONE 2026-07-13] "Under the hood (methodology)" flagged as low-value, reworked.** Guilherme
  didn't find it useful/understandable as-is and expected it to be reshaped once there was a
  clearer idea of what should replace it — that idea arrived during 2026-07-13's pitch-prep
  session (a request for a fuller "about the project" page, plus whole-number headline stats over
  decimal ML scores). Split in two: a new **"About & Roadmap"** sidebar view
  (`render_about_and_roadmap` in `app.py`) now carries the framework explanation, a "What's been
  built" whole-number stat row, the FRAMEWORK.md worked example, a "how to use this app" guide, a
  plain-language shipped/next-up summary, and a collapsed **"Methodology"** expander — the only
  place decimal stats (ROC-AUC, Brier, silhouette, the Phase 4c per-tournament generalisation
  table/chart) still appear, each explained inline. The old per-player `st.expander("Under the
  hood (methodology)")` at the bottom of the Player explorer page is slimmed to a one-line pointer
  at the new tab plus the one thing genuinely specific to that page: the current position group's
  live silhouette curve.
- **[DONE 2026-07-13] Goalkeepers wired into the app.** `src/app_data.py`'s new
  `_build_combined_gk_table` runs `build_goalkeeper_per90_features` across the same
  `config.SIMILARITY_SETS` pool and concatenates onto the outfield table (no `config.py` change
  needed — the existing dataset registry was reusable as-is). `app.py` gained a 4th position-filter
  option (Goalkeeper, 124 players), its own `SIGNATURE_STATS_BY_POSITION` entry, GK-specific radar
  axes (moved the radar-axes widget to render after the player is picked, since its options now
  depend on position group), a `save_pct` caption in place of the outfield penalty breakdown, and a
  branch in the "All per-90 stats" expander and "players like X" call. **Deliberately not
  clustered** — no K/silhouette decision made for goalkeepers yet, so there's no style-archetype
  layer for them (only outfield players have one); "players like X" still works since
  `find_similar_players` ranks by raw distance, not cluster membership. A real bug, caught by
  Streamlit's `AppTest` harness rather than by reading the diff: `build_goalkeeper_per90_features`
  only returned `_p90` rate columns, not the raw season totals the signature-stat cards need
  (unlike the outfield builder) — fixed in `src/similarity.py`. See PROGRESS.md and
  ML_LEARNING_LOG.md for the full account.
- **[DONE 2026-07-09] Clickable "similar player" names** — jump from the "players like X" list
  into that player's own page (and see *their* similar players — a recursive drill-down). Shipped
  via the "Table view" `st.dataframe`'s `on_select="rerun", selection_mode="single-row"` (the
  static `plot_similar_players_bar` chart itself stays non-interactive; the table below it is the
  click target). Row click → `st.session_state["jump_to_player"]` → `st.rerun()` → a top-of-script
  block pre-seeds the sidebar filters/search/selectbox before they're created, landing on the
  target player. Recursive drill-down confirmed working (clicked twice in a row: Fallou Diagne →
  Aïssa Mandi → back to Fallou Diagne). A real bug surfaced during verification — a fixed
  `st.dataframe` `key` persisted row-selection state across players and caused an infinite jump
  cascade — fixed by scoping the key to `player_name`/`team_name`. See PROGRESS.md for the full
  account, including a minor open cosmetic follow-up (the "Table view" expander's open/closed
  state doesn't always carry over consistently across a jump).
- **[DONE 2026-07-09] Penalty info on the player page** (raised 2026-07-08). The single-player
  "Player explorer" page showed only `non_penalty_goals` and nothing about penalties or total
  goals — so the page looked like it had *no* penalty data even though the leaderboard total
  included them. Shipped as a `st.caption` right under the existing "Season totals..." caption
  (`app.py`, after the signature-stats metric-card loop): `"Goals (incl. penalties): {total}
  ({n} from penalties)"`, using the `goals`/`non_penalty_goals` columns already on
  `player_row_full` — presentation-only, no data/rebuild work, as anticipated. Only rendered when
  `total_goals > 0`, so non-scorers' pages are unaffected. Verified live via
  `streamlit run app.py` + the Playwright-over-Edge recipe (see PROGRESS.md).

### Visual/brand pass — 2026-07-13 (cont. 4)

A same-day follow-up, after the goalkeeper wiring above, asked for: Leaderboard filters (name +
position), a stronger Player explorer intro, a more visually developed sidebar/header with a
brand icon and slogan, and an expanded About & Roadmap covering data/methods/direction. All four
shipped in `app.py`:

- **Leaderboard filters:** `render_leaderboard` gained an in-page `st.text_input` (name) and
  `st.multiselect` (position, defaulting to all options) above the table — additive to, not a
  replacement for, the sidebar's existing position/competition filters, since those narrow the
  *whole* player pool (shared with Player explorer) while these two are Leaderboard-only.
- **Player explorer intro:** previously had no page-level title or explanation at all — a bare
  search box. Now opens with `render_page_header("Player explorer")` plus a short markdown intro
  naming every panel the page contains.
- **Brand identity:** two new module constants, `BRAND_ICON = "⚽"` and
  `SLOGAN = "Scout by data, not by reputation."`, used in the browser tab (`page_icon`), a new
  `render_page_header()` helper (title + a top-right icon/slogan badge, used by the Leaderboard,
  Player explorer, and per-player pages), and an enriched sidebar (brand header, two live
  `st.metric` quick-facts computed from `per90`/`metrics.json` rather than hardcoded, a "New here?"
  pointer to About & Roadmap, and a GitHub source link).
- **About & Roadmap expansion:** two new visible (non-collapsed) sections, "Data used" (the actual
  competitions/seasons behind each model, per [DATA.md](DATA.md)) and "How each model works" (a
  qualitative K-means/Euclidean-distance/PCA description for similarity, logistic regression for
  xG) — both prose/dataset-name content, no bare decimals, so they don't conflict with the
  whole-number-headline rule the "Methodology" expander already follows. The "what's next" roadmap
  paragraph was also expanded into three tiers (small/open, bigger modelling upgrades, and a new
  "third lens, not started" paragraph naming Module C/PUP explicitly — it hadn't been mentioned
  anywhere in the app before this pass).

Verified via a scripted `AppTest` pass over all three views plus the two new Leaderboard filters
and a goalkeeper pick (no exceptions), then Playwright-over-Edge screenshots of all three pages —
see PROGRESS.md.

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

Expanded from the [FRAMEWORK.md](FRAMEWORK.md#product-layer-planned) sketch. A left **sidebar** drives
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
- [x] **Deploy to Streamlit Community Cloud; put the URL in `README.md` and the portfolio**
      (2026-07-09) —
      [gpfootball-analytics-portfolio.streamlit.app](https://gpfootball-analytics-portfolio.streamlit.app).
      Python 3.10 pinned explicitly in the deploy's advanced settings (Cloud's newer 3.14 default
      risked missing wheels for `kloppy`/`pyarrow`/`statsbombpy`, all pinned against 3.10 locally).
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
