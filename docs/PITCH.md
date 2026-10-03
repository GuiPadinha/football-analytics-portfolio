# Pitch Cheat Sheet

→ [CLAUDE.md](../CLAUDE.md) | Phase status: [ROADMAP.md](ROADMAP.md) | Framework: [FRAMEWORK.md](FRAMEWORK.md)

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

1. **Leaderboard** — scale (9 competitions, 2,170 players), sort by Goals, point out a
   penalty-inflated total (e.g. a defender whose goals are mostly penalties) — shows why "raw
   goals" is a misleading stat on its own. Mention the name/position filters above the table if
   asked how to find a specific player quickly.
2. **Player explorer, pick a well-known forward** — radar vs. position peers, signature stats.
3. **Style archetype** (2026-07-13) — the chart right below signature stats: this player's cluster,
   auto-described by which stats it over/under-indexes on (e.g. "high Key Passes, low Clearances").
   Good line: "the model isn't just handed a role label — it *finds* the archetype from the stats,
   then explains itself." Click into "Browse this archetype" to show a few other players in the
   same style bucket.
4. **"Players like X"** — click a row in the table, show the recursive drill-down (jumps to the
   similar player, recomputes everything for them). Point out the **Market value** column
   (2026-07-14) — this is the "who else plays like them, ideally cheaper?" pitch line answered
   with a real number, not just a vibe.
5. **"Finishing" panel** — goals vs. xG, shot map. This is the "is it real or luck" answer.
6. **Compare players** (2026-07-14) — pick two well-known names (works across positions/
   competitions), show the overlaid radar and the market-value delta line ("X is valued €Y less
   than Z"). A good closer beat: it's the two lenses *and* the new valuation feature on one screen.
7. Close on the credibility numbers below, then the roadmap.

---

## Key numbers to lead with (whole numbers — say these without notes)

- **9** competitions (5 of them women's), **2,170 players** in the similarity pool (incl. **168 goalkeepers**, wired in
  2026-07-13 with their own feature set — saves, goals conceded, claims, punches, sweeper actions,
  plus save % — and K-means clustered into style archetypes like the outfield groups).
- **10,824** shots trained the xG model; a further **7,215** held-out shots — across **6**
  tournaments it never trained on, **2 of them women's** — used to check it generalises.
- **1,327** players matched to a real Transfermarkt market value (men's competitions only, each
  confirmed at the player's club that season — see the Roadmap section below for the coverage caveat).
- **~170** automated tests, including smoke tests of every app view, run on every push on Python
  3.12 and 3.14; a one-command rebuild (`python -m src.pipeline`) that reproduces every number and
  chart byte-for-byte; and a live deployed app.

*(The first two lines are the app's "About & Roadmap" → "What's been built" tiles; market value
and test count aren't on-screen tiles but are just as safe to say from memory.)*

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
- **Generalisation, not a one-off:** the same trained model, never retrained, ranks shots just as
  well on five more tournaments it never saw (0.76–0.81 ROC-AUC). That includes two **women's**
  tournaments: 0.777 at the 2023 Women's World Cup, 0.763 at Women's EURO 2025. It doesn't
  under-predict women's goals either (Women's EURO: 98% of xG scored). Don't call EURO 2024 "the
  floor": Copa América (0.763) is a hair lower.
- **Similarity's honest caveat:** silhouette score (cluster tightness) peaks low, ~0.22–0.26 —
  stated plainly rather than hidden: play styles within a position are a soft continuum, not sharp
  clusters. K=4 is still used, for archetype granularity, against the metric's own preference for
  K=2.

---

## Roadmap to show (what's next)

- **Open backlog (small):** the cross-league normalisation is a *relative* (z-score) adjustment,
  not a true competitiveness rating — there's no external league-strength data behind it. Market-
  value matching is name-based (no shared player ID exists) — a real match can be missed on a
  name/position collision, and women's-league players have no market value at all (the
  Transfermarkt mirror used here only covers men's football).
- **Phase 5 (not started):** uncertainty on the xG number (bootstrap intervals), a hierarchical
  finishing model — "is this player's over/underperformance statistically real."
- **Phase 6 (not started):** Mahalanobis/PCA-whitened distance for similarity (today's Euclidean
  double-counts correlated stats), possession-adjusted defensive actions.
- **Phase 7 (not started):** 360°-context xG (defender positions at the moment of the shot) +
  post-shot xG (xGOT).
- **Phase 9 (opportunistic):** an xA/chance-creation model, a 2026 World Cup predictive model
  (data-availability check first).

Full phase-by-phase detail: [ROADMAP.md](ROADMAP.md) (status table, milestones, per-phase task
lists).

---

## If asked "why isn't X done yet"

- **Cross-league normalisation (Phase 4b):** resolved 2026-07-13 — per-90 rates are now
  league-adjusted (z-scored within each competition) before comparing across the 9-competition
  pool. Still a relative, data-only fix, not a true competitiveness rating — flagged honestly
  in-app, not oversold as a full solution.
- **Market value modelling** (not *displaying* one — that's done, see above): still out of scope
  by design. This tool informs a human's valuation, it doesn't price players itself.
- **If a specific player's market value is missing:** either no confident match (no shared player
  ID exists between StatsBomb and Transfermarkt, so exactly one name match must show the player at
  the same club that season — see DATA.md) or a women's-league player (zero coverage there). Never a
  guessed number.
