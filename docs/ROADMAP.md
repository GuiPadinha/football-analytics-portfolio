# Session Roadmap & Initiative Status

→ [CLAUDE.md](../CLAUDE.md) | Initiative detail: [INITIATIVE.md](INITIATIVE.md)

---

## Session Roadmap (S1–S9)

| Session | Focus | Status |
|---|---|---|
| S1 | Scaffold + data exploration | ✅ Done |
| S2 | xG feature engineering | ✅ Done |
| S3 | xG model — baseline | ✅ Done |
| S4 | xG model — upgrade + visuals | ✅ Done |
| S5 | Player similarity — features | ✅ Done |
| S6 | Player similarity — clustering | ✅ Done |
| S7 | Radar charts + visuals | ✅ Done |
| S8 | README + polish | ✅ Done |
| S9 (future) | Module C — PUP | 💡 Scoped only |

---

## Framework Hardening & Expansion Initiative

Kicked off post-S8 (2026-06-29). On 2026-07-02 the full code-review backlog was folded into one
execution-ordered program and renumbered to Phases 0–9.

**The phase table + status lives only in [INITIATIVE.md](INITIATIVE.md#L18) — do not duplicate it
here.** This doc holds the *detailed task lists* per phase. Execution order: 0→1→2→3→4→5→6→7→8,
with 9 opportunistic. Phases 0–2 are done.

---

## Phase 3 — Engineering & reproducibility spine  ⬜ Next

Cheapest credibility badge for the target roles, and it structurally kills the doc drift so every
later phase writes into a single-source system. Goes first because 3e (manifest) is a prerequisite
of Phase 4's ingestion pipeline and 3b (`metrics.json`) must exist before the data/number 10×.

- **3a — De-drift** (docs done 2026-07-02): canonical phase table in INITIATIVE; ROADMAP links to
  it; Exhibit A fixed in PROGRESS.md; CLAUDE Current Status renumbered; FRAMEWORK/PRODUCT_SPEC
  product refs → Phase 8. *Leftover for the Phase 3 code session:* renumber the two stale
  `src/config.py` comments that call the 360 model "Phase 3" (now Phase 7) — deferred to keep the
  2026-07-02 commit docs-only.
- **3b — `metrics.json` single source:** tests/notebook emit key numbers (ROC-AUC, Brier, CV±,
  silhouette, test count) to a small `metrics.json`; docs reference it. Optional doc-lint test that
  fails if a doc's number diverges from the file.
- **3c — CI:** `.github/workflows/tests.yml` runs the 22 pytest tests on push/PR (Python 3.10,
  pinned `requirements.txt`); green badge in README.
- **3d — `pipeline.py` + `Makefile`:** headless rebuild of ingestion → features → model → outputs,
  no notebook execution required. Notebooks **stay** as the teaching surface (learning mandate) —
  the pipeline runs alongside them.
- **3e — Data manifest:** `data/manifest.json` pinning comp/season/match IDs + row counts + content
  hash per dataset; catches upstream StatsBomb changes; feeds Phase 4.

## Phase 4 — Multi-competition ingestion + data expansion  ⬜

The flagship overlap item: engineering-at-scale in service of ML. Fixes Module B's single-season
thinness and turns Module A's "generalises from n=2 contexts" into a defensible claim.

- **4a — Config-driven ingestion:** generalise `data_loader.py` + the `src/config.py` `Dataset`
  registry (already the right shape; `SIMILARITY_SET` literally says "widened in Phase 4") so a new
  competition is a config line, not a code edit. Manifest-tracked (reuses 3e).
- **4b — Module B cross-league/season:** the structural fix — single-season similarity can't do
  "cheaper version in a smaller league." Add competitions; design league-context/strength
  normalisation so per-90 profiles compare across leagues.
- **4c — Module A generalisation:** add held-out test contexts beyond the single EURO 2024.
- **4d — Availability friction:** free full-season league data is scarce and skews to Messi-era La
  Liga (CONTEXT.md says avoid); tournaments are plentiful but wrong-shaped for per-90 similarity.
  Pick deliberately, document the constraint.

## Phase 5 — xG uncertainty + hierarchical finishing model  ⬜

The ML-depth differentiator: small → big, no new data, directly serves the valuation lens.

- **5a — Uncertainty on goals−xG:** bootstrap / analytic interval so "+8 on 40 shots" and "+8 on
  200 shots" stop reading as the same claim. The single best small addition.
- **5b — Hierarchical / empirical-Bayes finishing:** per-player finishing random effect over
  baseline xG, shrunk toward zero — the statistically correct goals−xG. Achieves PUP's "real or
  luck" with clean stats. (May add `statsmodels`.)
- **5c — Header/foot interaction (or split models):** one `body_part` flag assumes identical
  geometry→goal curves for headers and volleys; add an interaction or split.
- **5d — Calibration by stratum:** reliability diagrams split open-play / set-piece / header to
  expose miscalibration the single Brier number hides.

## Phase 6 — Module B metric/feature upgrades  ⬜

- **6a — Mahalanobis / PCA-whitened distance:** Euclidean double-counts correlated features
  (shots↔goals, tackles↔interceptions); respect the covariance.
- **6b — Possession-adjusted defensive actions:** per-100-opponent-touches so a presser at a
  possession side and one at a low block compare fairly.
- **6c — GMM soft membership:** the ~0.25 silhouette (continuum) motivates it; also dissolves the
  Antonio one-man-cluster.
- **6d — Richer creative features:** xA / progressive-pass-distance over raw key passes.

## Phase 7 — 360-context xG + xGOT  ⬜  *(was Phase 3)*

StatsBomb `three-sixty` data gives freeze-frames (every visible player's position at the moment of each event). Leverkusen 2023/24 and EURO 2024 both have 360 — the two datasets already in use.

**Candidate 360 features:**
- Number of defenders between shot and goal (direct block probability)
- Goalkeeper position relative to goal centre
- Number of open-goal-path defenders
- Nearest defender distance to ball at shot moment

**Post-shot xG (xGOT):** shot trajectory context (where the ball ended up, keeper reaction) narrows the probability *after* the shot is taken. Distinction: pre-shot xG (chance quality before kick) vs. xGOT (includes where the shot went).

**Recommended approach:** keep the existing pre-shot logistic model as the baseline. Build 360-feature extension as a second model. Compare honestly — if the 360 features don't clearly add discrimination, say so.

**Entry checklist:**
- [ ] Confirm Phase 3–6 work committed via GitHub Desktop
- [ ] Verify `data/cache/` has Leverkusen 2023/24 360 frames (should already be pulled)
- [ ] Check StatsBomb `three-sixty` schema: `statsbombpy.sb.three_sixty(match_id=X)`

## Phase 8 — Product layer build (Streamlit)  🟡 spec done  *(was Phase 5)*

Execute the existing [PRODUCT_SPEC.md](PRODUCT_SPEC.md) build checklist (`app_data/` build step,
`app.py`, theme, radar-axis multiselect, "under the hood" expander, deploy, README URL). Comes
after 4–6 so it showcases the *upgraded* models, not the current ones.

## Phase 9 — Opportunistic  ⬜

- **xA / chance-creation model** — sibling to xG on the same pipeline; also upgrades 6d.
- **Module C (PUP)** — only if desired; carries a selection-bias confound + label-acquisition cost,
  and Phase 5 already delivers most of its payoff. Spec: [MODULES.md](MODULES.md#L53).
- **Remaining alt-models** — hierarchical clustering, cosine, monotonic GBM.
