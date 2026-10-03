# Product Layer — the Streamlit App (Phase 8)

→ [CLAUDE.md](../CLAUDE.md) | Framing: [FRAMEWORK.md](FRAMEWORK.md) | Phases: [ROADMAP.md](ROADMAP.md#phases)

**Status:** live at
[gpfootball-analytics-portfolio.streamlit.app](https://gpfootball-analytics-portfolio.streamlit.app)
since 2026-07-09 (Streamlit Community Cloud; redeployed on Python 3.14 on 2026-10-03, see
ROADMAP.md's Phase 9). This file describes the app **as it is**. How it got here, session by session, is in
[PROGRESS.md](PROGRESS.md) / [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md). The design decisions
worth not re-litigating are in the **UX decision log** below.

---

## Purpose and audience

Turn two analyses into one tool: a URL where someone can pick a player and immediately see "who
plays like this" (Module B) and "is their output real or luck" (Module A). Two audiences, neither
of whom reads Python: **interviewers/recruiters** (proof the models work end to end and that the
author ships products, not notebooks) and **football fans** ("pick your favourite player" is
self-explanatory). So the screen has to explain itself, and headline numbers are whole-number
counts. Decimal model scores (ROC-AUC, Brier, silhouette) live only in the Methodology expander,
next to what they mean.

---

## Views

A sidebar radio switches between four views. Sidebar filters (position group, competition)
narrow the pool for Player explorer and Leaderboard; Compare players always searches everyone.

**Player explorer** — one player, deep dive. A live-filtering search box (starts blank), then:
1. **Scouting report** — one templated paragraph stitched from the panels below (style traits,
   best percentile, market value). It's not an LLM summary and adds no new number.
2. **Signature stats** — three role-specific season totals per position group, with the per-90
   rate and a percentile + tier word on hover. Below: goals incl. penalties (outfield) or save %
   (goalkeepers), and the Transfermarkt market value with the matched name and date.
3. **Style archetype** — the player's K=4 cluster in plain words ("noticeably more X and Y, less
   Z"), with the exact σ values in an expander and a click-to-jump list of others in the archetype.
4. **All per-90 stats** — a percentile bar chart (higher is always better, lower-is-better stats
   flipped) plus a table view.
5. **Radar** vs. position peers (axes chosen in the sidebar) and **Players like X**: the five
   nearest neighbours in league-normalised feature space, with market value. Clicking a row jumps
   to that player's page (a recursive drill-down).
6. **Finishing** — goals, xG, goals−xG and a shot map, for players in the xG training set
   (PL 2015/16 + Leverkusen 2023/24). Everyone else gets an explicit "no logged shots" note.
7. A collapsed **Under the hood** expander with this position group's silhouette curve.

**Leaderboard** — every player in the current filters in one sortable table: minutes, goals (incl.
penalties), non-penalty goals, assists, xG, G−xG (diverging colour), market value (€M). In-page
name and position filters sit on top. Missing values are blank (goalkeepers have no goals/assists,
most of the pool has no xG); every column sorts numerically.

**Compare players** — any two players. Market value and Finishing always compare. Signature stats,
an overlaid radar and a percentile table appear only when both share a position group (otherwise
the stats aren't the same).

**About & Roadmap** — what the tool is, how to use it, whole-number "what's been built" tiles,
the data used, how each model works, what's shipped / next, and a **Methodology** expander with
the xG metrics, the per-tournament generalisation table + chart, and the similarity caveats.
Every number comes from `metrics.json`, none hand-typed.

---

## Component → backend map

The app is a thin shell: every panel calls an existing, tested `src/` function. The words around
the numbers come from `src/presentation.py`.

| Panel | Backend | File |
|---|---|---|
| Player pool, per-90 stats, clusters | `build_player_per90_features`, `build_goalkeeper_per90_features`, `normalize_within_competition`, `fit_kmeans` (precomputed by `src/app_data.py`) | [similarity.py](../src/similarity.py), [app_data.py](../src/app_data.py) |
| Percentiles + tier words | `goodness_percentiles`, `percentile_tier`, `format_percentile` | [similarity.py](../src/similarity.py), [presentation.py](../src/presentation.py) |
| Style archetype | `profile_clusters`, `style_intensity_label`, `plot_diverging_bar` | [similarity.py](../src/similarity.py), [presentation.py](../src/presentation.py), [visualisation.py](../src/visualisation.py) |
| Scouting report | `build_scouting_blurb` | [presentation.py](../src/presentation.py) |
| Radar / comparison radar | `plot_player_radar`, `plot_player_radar_comparison` | [visualisation.py](../src/visualisation.py) |
| Players like X | `find_similar_players`, `plot_similar_players_bar` | [similarity.py](../src/similarity.py), [visualisation.py](../src/visualisation.py) |
| Finishing + shot map | `build_player_xg_table` (precomputed), `plot_shot_map` | [models.py](../src/models.py), [visualisation.py](../src/visualisation.py) |
| Market value | `build_market_value_table` (precomputed), `lookup_market_value`, `format_market_value` | [market_value.py](../src/market_value.py), [presentation.py](../src/presentation.py) |
| Methodology | `metrics.json`, `plot_xg_generalisation_bar`, `compute_silhouette_scores`, `plot_silhouette_curve` | [metrics.py](../src/metrics.py), [visualisation.py](../src/visualisation.py) |

(Function names instead of `#L` line anchors: anchors drifted as files grew, and 4 of the 8 old
ones pointed at the wrong line by 2026-09-30.)

---

## Data flow and runtime

The app **reads precomputed artifacts and never downloads anything**. A hosted demo must respond
to a click, not to a multi-minute StatsBomb pull.

```
src/ (offline, slow)  ──python -m src.app_data──►  app_data/*.parquet  ──st.cache_data──►  app.py
                                                   (committed, ~1 MB)        (instant)
```

- `app_data/` holds four Parquet files: the player pool with clusters, the flagship xG table, the
  shots with predicted xG, and market values. It is committed because it is small enough not to
  need Git LFS. The app also reads `metrics.json`.
- `requirements.txt` is the app's runtime only, which is exactly what Streamlit Cloud installs.
  CI's `app-runtime` job installs just that file and smoke-tests every view
  (`tests/test_app_smoke.py`). If the app ever imported a dev-only package, CI would fail before
  the deployment did.
- Theme: `.streamlit/config.toml` (dark teal/orange). `app.py` mirrors the same palette in
  matplotlib's rcParams so the charts match the chrome.

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
  trick doesn't apply. Three options are weighed in ROADMAP.md's Phase 9 list; none is chosen.
- **Blank, not "None", in tables.** The fix is `st.dataframe(..., placeholder="")`, with numeric
  columns kept numeric so header-click sorting stays numeric. From 2026-07-13 to 2026-10-01 a
  text-column workaround was used instead, on the mistaken belief that no config fix existed (see
  ML_TOOLING.md).
- **Percentiles mean "better than peers", always.** Lower-is-better stats (goals conceded) are
  flipped (`goodness_percentiles`), and every percentile carries a tier word (Elite … Poor), so a
  bare "72nd" never has to carry the judgement alone.
- **Style archetype leads with words, not σ.** "+1.4σ" read as jargon; the numbers are one click
  away. A z-score has no good/bad direction, so the words describe *how unusual*, not *how good*.
- **Drill-down tables key their selection state per player.** A fixed `key` kept "row 0 selected"
  on the new page and cascaded into an endless jump. This was caught by clicking through in a
  browser.
- **Whole numbers up front, decimals in Methodology.** The headline tiles are things that can be
  said without notes; ROC-AUC/Brier/silhouette appear only with their explanation.
- **Market value is displayed, never modelled.** It is a matched external Transfermarkt figure,
  blank unless exactly one name match is placed by Transfermarkt at the player's club that season,
  or when the league isn't covered (women's football). It is never guessed.
- **Goalkeepers get their own feature set**, not a branch of the outfield one (a keeper's tackles
  are noise).

---

## Known gaps

- The "Table view" expander's open/closed state doesn't always survive a drill-down jump (cosmetic).
- No pass-completion % or duel-success %: those need *attempted*-action features from raw events,
  not a new chart.
- Market value: 20 of 1,347 men's players stay blank (no single Transfermarkt profile at their
  club that season), and there is no women's coverage (see DATA.md).
- The live demo sleeps after inactivity, so the first visit waits about a minute (see ROADMAP.md's
  Phase 9 list).
- No SkillCorner physical panel: that data shares no players with the event data.

## Out of scope

Live StatsBomb pulls or retraining inside the app; accounts, auth or saved sessions; 360-context
xG / xGOT panels until Phase 7 exists.
