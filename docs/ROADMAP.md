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

Kicked off post-S8 (2026-06-29). Six phases targeting code-review findings, product clarity, 360-context xG, and more data.

| Phase | Focus | Status |
|---|---|---|
| 0 | Charter: FRAMEWORK.md, INITIATIVE.md, CLAUDE.md roadmap | ✅ Done |
| 1 | Foundation: config.py, per-match cache, penalty/shootout fix, tests, pinned deps | ✅ Done |
| 2 | ML rigor: scaled logistic, CV, baseline ladder, calibrated GBM, silhouette, minutes-weighted positions | ✅ Done |
| 3 | New model: 360-context xG + post-shot xG (xGOT) | ⬜ **Next** |
| 4 | More data + cross-league/season normalisation | ⬜ Not started |
| 5 | Product layer: interface spec + lightweight Streamlit app ([PRODUCT_SPEC.md](PRODUCT_SPEC.md)) | 🟡 Spec done, build pending |
| 6 | Alternative models (GMM, hierarchical, cosine, monotonic GBM) | ⬜ Opportunistic |

---

## Phase 3 Scope — 360-context xG + xGOT

StatsBomb `three-sixty` data gives freeze-frames (every visible player's position at the moment of each event). Leverkusen 2023/24 and EURO 2024 both have 360 — the two datasets already in use.

**Candidate 360 features:**
- Number of defenders between shot and goal (direct block probability)
- Goalkeeper position relative to goal centre
- Number of open-goal-path defenders
- Nearest defender distance to ball at shot moment

**Post-shot xG (xGOT):** shot trajectory context (where the ball ended up, keeper reaction) narrows the probability *after* the shot is taken. Distinction: pre-shot xG (chance quality before kick) vs. xGOT (includes where the shot went).

**Recommended approach:** keep the existing pre-shot logistic model as the baseline. Build 360-feature extension as a second model. Compare honestly — if the 360 features don't clearly add discrimination, say so.

---

## Phase 3 — Entry Checklist

Before starting Phase 3:
- [ ] Confirm all Phase 1+2 work committed via GitHub Desktop
- [ ] Read [docs/INITIATIVE.md](INITIATIVE.md) for any pre-work notes on Phase 3
- [ ] Verify `data/cache/` has Leverkusen 2023/24 360 frames (should already be pulled)
- [ ] Check StatsBomb `three-sixty` schema: `statsbombpy.sb.three_sixty(match_id=X)`
