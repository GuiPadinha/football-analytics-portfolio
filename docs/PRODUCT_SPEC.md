# Product Layer — the Streamlit App (Phase 8)

→ [CLAUDE.md](../CLAUDE.md) | Framing: [FRAMEWORK.md](FRAMEWORK.md) | Phases: [ROADMAP.md](ROADMAP.md#phases)

**Status:** live at
[gpfootball-analytics-portfolio.streamlit.app](https://gpfootball-analytics-portfolio.streamlit.app)
since 2026-07-09 (Streamlit Community Cloud; redeployed on Python 3.14 on 2026-10-03, redesigned
"conclusions first" on 2026-10-10, see ROADMAP.md's Phase 9). This file describes the app **as it is**. How it got here, session by session, is in
[PROGRESS.md](PROGRESS.md) / [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md). The design decisions
worth not re-litigating are in the **UX decision log** below.

---

## Purpose and audience

Turn two analyses into one tool: a URL where someone can pick a player and immediately see "who
plays like this" (Module B) and "is their output real or luck" (Module A). Two audiences, neither
of whom reads Python: **interviewers/recruiters** (proof the models work end to end and that the
author ships products, not notebooks) and **football fans** ("pick your favourite player" is
self-explanatory). So the screen has to explain itself and lead with conclusions. Method (σ, distances, silhouette,
ROC-AUC) lives on the How it works page, next to what each number means.

---

## Views

Top navigation (`st.navigation(position="top")`): Home, Players, Compare, Leaderboard, How it works.
Each page is a script under `views/`; `app.py` is only the frame and the stylesheet.

**Home** — a search box, a strip of whole-number facts, and four *computed* finding cards (the
biggest finishing over- and under-performer, how often a valued man has a half-price lookalike, the
closest man-woman pair), each with its caveat, then a three-step "how it works". Cards come from
`app_data/findings.json` (`src/findings.py`).

**Players** — one player as three questions, under a "short version" paragraph (`narrative.py`):
1. **What kind of player?** "Does more / less than most": top N% / bottom N% bars on
   league-adjusted percentiles, with the raw per-90 rate and season total under each.
2. **Are the goals real?** Goals, the goals the chances were worth, the gap, an exact-odds sentence
   and a native shot map. Players outside the Premier League 2015/16 get a plain "no shot data"
   panel; keepers get "how good is the shot-stopping?" (save %, saves, shots on target).
3. **Who plays like this?** Men's and women's top-5 lists in tabs (the player's own game first),
   how-close bars, Transfermarkt value and a "Cheaper" tag, and a note that a similar style is not
   the same level. A name opens that player's page. A button starts Compare with this player.
A player's header shows popular name, team, facts and market value (or why there isn't one).

**Compare** — any two outfield players (whatever their position) or any two goalkeepers: a card
each, a rule-based verdict, per-90 bars side by side, and goals against chances (or save %). A
keeper against an outfielder gets a plain warning.

**Leaderboard** — everyone in one sortable table: minutes, goals (incl. penalties), assists,
goals − xG (Premier League only), value (€M). Filters for game, position and name; a row opens the
player. Blank means not available, never guessed.

**How it works** — the data, how each of the three answers is made, the shot model's accuracy
(`metrics.json` plus a per-tournament chart), style-group silhouettes and the limits, stated plainly.

---

## Component → backend map

The pages are thin: what they say is decided in tested `src/` functions.

| Panel | Backend | File |
|---|---|---|
| Player pool, per-90 stats, clusters | `build_player_per90_features`, `build_goalkeeper_per90_features`, `normalize_within_competition`, `fit_kmeans` (precomputed by `src/app_data.py`) | [similarity.py](../src/similarity.py), [app_data.py](../src/app_data.py) |
| Percentile bars (league standing) | `league_adjusted_percentiles`, `profile._stat_bars`, `top_share` | [similarity.py](../src/similarity.py), [profile.py](../src/profile.py), [narrative.py](../src/narrative.py) |
| Short version | `build_short_version` (style, finishing or saves, price or closest match) | [narrative.py](../src/narrative.py) |
| Finishing + shot map | `finishing_from_shots` (exact odds), `describe_finishing`, `components.shot_map` | [narrative.py](../src/narrative.py), [components.py](../views/components.py) |
| Lookalikes | `rank_matches` split by `config.GENDER_BY_COMPETITION` | [similarity.py](../src/similarity.py), [profile.py](../src/profile.py) |
| Compare verdict | `pair_closeness`, `build_compare_verdict` | [similarity.py](../src/similarity.py), [narrative.py](../src/narrative.py) |
| Home cards | `findings.build_findings` → `app_data/findings.json` | [findings.py](../src/findings.py) |
| Leaderboard | `profile.build_leaderboard` | [profile.py](../src/profile.py) |
| Market value | `build_market_value_table` (precomputed), `profile.market_value_of` | [market_value.py](../src/market_value.py) |
| How it works | `metrics.json`, `compute_silhouette_scores` | [metrics.py](../src/metrics.py), [similarity.py](../src/similarity.py) |

---

## Data flow and runtime

The app **reads precomputed artifacts and never downloads anything**. A hosted demo must respond
to a click, not to a multi-minute StatsBomb pull.

```
src/ (offline, slow)  ──python -m src.app_data──►  app_data/*.parquet + findings.json
                                                          │  views/data.py (st.cache_*)
                                                          ▼
                                       profile.py / narrative.py ──► views/*.py ──► browser
```

- `app_data/` holds four Parquet files (player pool with clusters, the Premier League xG table, the
  shots with predicted xG, market values) and `findings.json`. It is committed because it is small
  enough not to need Git LFS. The app also reads `metrics.json`.
- `requirements.txt` is the app's runtime only, which is exactly what Streamlit Cloud installs. It
  has no matplotlib: the app draws with Altair, which Streamlit installs. CI's `app-runtime` job
  installs just that file and smoke-tests every page (`tests/test_app_smoke.py`), so a dev-only
  import fails CI before it fails the deployment.
- Theme: `.streamlit/config.toml` and `views/components.py`'s stylesheet share one palette (orange
  for "above", blue for "below", each pair also differing in lightness).

---

## Technology choice

**Streamlit**, because it is Python-native: it imports `src/` directly, with zero rewrite of model
logic, and the "pick a player → everything recomputes" interaction is its sweet spot. It also has
free hosting with one shareable URL. The trade-off is a somewhat generic look, mitigated by the
custom theme. Rejected: **Plotly Dash** (more layout control, materially more callback code for a
solo project) and a **static site** (snappiest, but kills live interactions like the radar-axis
picker and the drill-down).

---

## UX decision log

Decisions that were tried, reversed or deliberately chosen. Check here before "fixing" one of
them again.

- **Search box (three rounds).** Round 1 (2026-07-05) was a bare `st.selectbox`, pre-filled. It
  was rejected because it "reads as a dropdown, not a search box". Round 2 was `st.text_input` +
  selectbox. It was rejected on 2026-07-14 because `text_input` only reruns on Enter/blur, so
  typing looked broken. Round 3 (current) is a single selectbox that **starts blank**
  (`index=None`) and filters client-side as you type. That was confirmed with Guilherme before
  shipping, given round 1's history.
- **Leaderboard name filter still needs Enter.** It feeds a multi-row table, so the selectbox
  trick doesn't apply (labelled "press Enter").
- **Blank, not "None", in tables.** The fix is `st.dataframe(..., placeholder="")`, with numeric
  columns kept numeric so header-click sorting stays numeric. From 2026-07-13 to 2026-10-01 a
  text-column workaround was used instead, on the mistaken belief that no config fix existed (see
  ML_TOOLING.md).
- **Conclusions first, method last** (2026-10-10, after "numbers, no insights, cheap-looking").
  Every page opens with a sentence or a headline figure that says something; σ, distances,
  silhouettes and ROC-AUC live only on How it works. The old radar, percentile chart and sidebar
  filters were dropped from player pages with the redesign (the percentile bars and the search box
  cover what they did).
- **Percentiles rank league standing and read "top N%".** "Better than peers" is always the
  direction (goals conceded is ranked in reverse), the ranking is within the player's own league and
  position group (`league_adjusted_percentiles`: it moves a percentile by ~6 points on average
  versus pooled raw rates), and the rate shown next to it stays the real per-90 number. The
  Elite/Very good tier words were dropped: "top 4%" says it directly.
- **The text is rule-based, never an LLM.** Each sentence is a tested rule with named, calibrated
  thresholds (ML_LEARNING_LOG.md, 2026-10-06), so every claim traces to a number on the page.
- **Finishing is quoted as exact odds** ("about one season in 22"), not a z-score and not a bare
  "+6.5 goals" verdict: a season of shots barely separates skill from luck.
- **Lookalikes are two lists, men's and women's,** one ranking split by game; Compare reads one
  player's rank on the other's list ("5th-closest of 194 women's forwards"), because a distance
  cutoff called Benzema's 5th-closest match "different".
- **Prices carry a caveat next to them:** a similar style is not the same level. 94% of men valued
  at €10M+ have a half-price top-3 lookalike, so a cheap match is a lead, not a bargain.
- **A lookalike's name is a button keyed by game, rank and player**, and the page's search box is
  seeded from `selected_player` before it is drawn, so a jump shows who the page is about. (The old
  drill-down tables had a fixed `key` that kept "row 0 selected" on the new page and cascaded into
  an endless jump.)
- **Whole numbers up front, decimals on How it works.** The headline strip is things that can be
  said without notes; ROC-AUC/Brier/silhouette appear only with their explanation.
- **Market value is displayed, never modelled.** It is a matched external Transfermarkt figure,
  blank unless exactly one name match is placed by Transfermarkt at the player's club that season,
  or when the league isn't covered (women's football). It is never guessed.
- **Goalkeepers get their own feature set**, not a branch of the outfield one (a keeper's tackles
  are noise).

---

## Known gaps

- No deep links: a player's page has no URL of its own, so a link can't point at one (a
  `st.query_params` follow-up).
- 159 players have no StatsBomb nickname and a long registered name ("Mary Alexandra Earps"),
  mostly women's leagues. There is no safe rule for shortening a name.
- Goals against chances is Premier League 2015/16 only, and keepers have no shot-quality model.
- No pass-completion % or duel-success %: those need *attempted*-action features from raw events.
- Market value: 20 of 1,347 men's players stay blank (no single Transfermarkt profile at their
  club that season), and there is no women's coverage (see DATA.md).
- The live demo sleeps after inactivity, so the first visit waits about a minute (see ROADMAP.md's
  Phase 9 list).
- Home's finding cards are different heights, so their link buttons don't align (cosmetic).

## Out of scope

Live StatsBomb pulls or retraining inside the app; accounts, auth or saved sessions; 360-context
xG / xGOT panels until Phase 7 exists.
