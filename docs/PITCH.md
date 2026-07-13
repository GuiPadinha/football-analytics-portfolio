# Pitch Cheat Sheet

→ [CLAUDE.md](../CLAUDE.md) | Phase status: [INITIATIVE.md](INITIATIVE.md) | Framework: [FRAMEWORK.md](FRAMEWORK.md)

A living pre-demo cheat sheet, not enforced by the doc-freshness hook (it isn't a *current-state*
doc the metrics.json doc-lint checks, and it isn't append-only history like PROGRESS.md — it's a
talking-points sheet, refresh it by hand before each pitch). First written 2026-07-13 ahead of a
colleague pitch (date TBD — today or the next day at the time of writing).

---

## Elevator pitch (~30s)

> A recruitment-led player evaluation tool. It answers two questions a scout or analyst normally
> answers by "eye" — **"is this player's output real, or did they get lucky?"** (xG) and **"who
> else plays like them, ideally cheaper?"** (similarity). Two full ML pipelines on open StatsBomb
> data, deployed and live, not just notebooks.

**Live demo:** https://gpfootball-analytics-portfolio.streamlit.app
**Source:** https://github.com/GuiPadinha/football-analytics-portfolio

---

## Demo script (suggested order)

1. **Leaderboard** — scale (6 competitions, ~1,500 players), sort by Goals, point out a
   penalty-inflated total (e.g. a defender whose goals are mostly penalties) — shows why "raw
   goals" is a misleading stat on its own.
2. **Player explorer, pick a well-known forward** — radar vs. position peers, signature stats.
3. **"Players like X"** — click a row in the table, show the recursive drill-down (jumps to the
   similar player, recomputes everything for them).
4. **"Finishing" panel** — goals vs. xG, shot map. This is the "is it real or luck" answer.
5. Close on the credibility numbers below, then the roadmap.

---

## Key numbers to lead with (whole numbers — say these without notes)

- **6** competitions, **1,511** players in the similarity pool.
- **10,824** shots trained the xG model; a further **4,704** held-out shots — across **4**
  different tournaments the model never trained on — used to check it generalises.
- **72** automated tests, green on every push (CI), a reproducible one-command rebuild
  (`python -m src.pipeline`), and a live deployed app.

*(These are the numbers in the app's "About & Roadmap" → "What's been built" tiles — say them from
memory, no notes needed.)*

## Methodology backup — only if asked to justify the model

Don't lead with this; it's here so the underlying claim can be defended if someone asks "how do
you know the model is any good." Full detail + a per-tournament table also live in the app's
**About & Roadmap** → **Methodology** expander (source: `metrics.json`, single source — regenerate
via `python -m src.metrics`).

- **What ROC-AUC means:** how often the model correctly ranks a more dangerous shot above a less
  dangerous one. 1.0 = always right, 0.5 = a coin flip.
- **The xG model's score, and why it's earned, not free:** guessing the training goal rate for
  every shot scores 0.5 (no skill); shot geometry alone (distance + angle) already reaches 0.712;
  the full model (adds body part, assist type, game state) reaches 0.765 on the held-out EURO 2024
  test set.
- **Generalisation, not a one-off:** the same trained model, never retrained, scores 0.808 on FIFA
  World Cup 2022, 0.807 on Africa Cup of Nations 2023, 0.763 on Copa América 2024 (smallest sample,
  751 shots) — EURO 2024's 0.765 turns out to be the *floor* of the four, not a fluke.
- **Similarity's honest caveat:** silhouette score (cluster tightness) peaks low, ~0.22–0.26 —
  stated plainly rather than hidden: play styles within a position are a soft continuum, not sharp
  clusters. K=4 is still used, for archetype granularity, against the metric's own preference for
  K=2.

---

## Roadmap to show (what's next)

- **Open backlog (small, near-term):** goalkeepers not yet wired into the app; cross-league
  normalisation for similarity still open. (The methodology section already got its rework this
  session — see the new **About & Roadmap** view in the app.)
- **Backlog, bigger (not scoped further):** a side-by-side two-player comparison view.
- **Phase 5 (not started):** uncertainty on the xG number (bootstrap intervals), a hierarchical
  finishing model — "is this player's over/underperformance statistically real."
- **Phase 6 (not started):** Mahalanobis/PCA-whitened distance for similarity (today's Euclidean
  double-counts correlated stats), possession-adjusted defensive actions.
- **Phase 7 (not started):** 360°-context xG (defender positions at the moment of the shot) +
  post-shot xG (xGOT).
- **Phase 9 (opportunistic):** an xA/chance-creation model, a market-value integration (researched
  2026-07-13 — see [DATA.md](DATA.md#market-value-transfermarkt--flagged-2026-07-13-not-started)),
  a 2026 World Cup predictive model (data-availability check first).

Full phase-by-phase detail: [INITIATIVE.md](INITIATIVE.md) (status table + log) and
[ROADMAP.md](ROADMAP.md) (per-phase task lists).

---

## If asked "why isn't X done yet"

- **Women's EURO 2025 (Phase 4c, 1 of 4 tournaments):** genuinely rate-limited by StatsBomb's raw
  data host across several retries, not a shelved decision — resumable for free once the limit
  clears (per-match cache is already in place).
- **Cross-league normalisation (Phase 4b):** the similarity pool spans 6 competitions but compares
  raw per-90 rates across them — flagged honestly in-app, not silently assumed away.
- **Market value / transfer fees:** out of scope for *modelling* (this tool informs a human's
  valuation, it doesn't price players) — but *displaying* an external market-value number next to
  a similarity match was scoped 2026-07-13 as a good future addition; blocked on entity resolution
  between StatsBomb and Transfermarkt player identities, not on data availability.
