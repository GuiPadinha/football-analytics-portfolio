# Product Layer — Interface Spec (Phase 8)

→ [CLAUDE.md](../CLAUDE.md) | Framing: [FRAMEWORK.md](FRAMEWORK.md) | Phase tracker: [INITIATIVE.md](INITIATIVE.md)

**Status:** spec expanded 2026-07-01, build pending (Phase 8, after Phases 3–7). *(Renumbered from Phase 5 on 2026-07-02.)*
This is the *what* and the *why*. It writes no app code — it's the turnkey brief for
the future build session, plus mockups so the shape is agreed before a line is written.

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

- [ ] Add a `build step` (script or notebook cell) that writes the three artifacts to
      `app_data/` for at least the flagship dataset.
- [ ] Decide artifact shipping: committed `app_data/` vs. Git LFS (Open decision above).
- [ ] `app.py` (or `streamlit_app.py`): sidebar selectors → load cached artifacts →
      render the four panels via the reuse-map functions.
- [ ] `.streamlit/config.toml`: theme (colours, font) so it doesn't look stock.
- [ ] Radar-axis multiselect wired to `feature_columns` of `plot_player_radar`.
- [ ] "Under the hood" expander with the diagnostic plots.
- [ ] Add `streamlit` to `requirements.txt` (pinned).
- [ ] Deploy to Streamlit Community Cloud; put the URL in `README.md` and the portfolio.
- [ ] Smoke test: pick one player per position group, confirm all panels render with no
      empty-frame / KeyError on sparse columns.

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
