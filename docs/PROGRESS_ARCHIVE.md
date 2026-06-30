# Progress Log — Historical (S1–S8)

Sessions from 2026-06-28 through 2026-06-29. Committed work only.
→ Recent sessions: [PROGRESS.md](PROGRESS.md)

---

## 2026-06-28 — Dev environment setup

Fixed `python`/`pip` not recognized: added Python 3.10.7 (`C:\Users\guilh\AppData\Local\Programs\Python\Python310\` + its `Scripts\`) to User PATH; pinned as workspace interpreter in `.vscode/settings.json`. Fixed `CERTIFICATE_VERIFY_FAILED` from Avast intercepting HTTPS — appended Avast root cert to both `certifi` cacert.pem files. `pip install -r requirements.txt` now succeeds (new terminals only — already-open terminals won't pick up PATH change). S1 scaffold partially done (folders, `.gitignore`, `requirements.txt`, `src/data_loader.py` + module stubs) — notebook 01 still pending.

---

## 2026-06-29 — S1 + S2 + S3

**S1:** Notebook 01 ran clean; bonus mplsoccer shot map (all outcomes Goal/Saved/Blocked/Off T/Wayward explicitly coloured).

**S2** (`src/features.py`): distance/angle computed from goalpost geometry (StatsBomb pitch, posts at y=36/44); assist type derived by joining `shot_key_pass_id` to source pass event. Hit real bug: `pass_cross`/`pass_through_ball`/`pass_cut_back` hold `True`/`NaN` — `bool(NaN)` is `True` in Python, so ~72% of assists misclassified as crosses; fixed with explicit `is True` checks.

**S3** (`src/models.py`, `src/visualisation.py`, notebook 02): logistic regression on Leverkusen 2023/24 + PL 2015/16 (10,824 shots, 10.1% conversion), tested on EURO 2024 (1,340 shots) — ROC-AUC 0.786 train / 0.798 test. Cached to `data/shots_*.pkl`. Flagged `assist_type` dummy-variable collinearity for S4. Nothing committed yet.

---

## 2026-06-29 (cont.) — S4

Fixed assist-type collinearity (drop "None" as reference category). Added `train_gradient_boosting()`: tuning sweep; even tuned, GBM (train 0.796/test 0.793) didn't beat logistic (0.786/0.798) — **logistic stays as recommended model**. Added `get_feature_importance()`, `build_player_xg_table()`, `plot_player_xg_ranking()`. Rebuilt cache with `competition_id` column to isolate PL 2015/16 from Leverkusen for the era-benchmark ranking. PL 2015/16 ranking passes sniff test: Agüero/Mahrez/Kane top overperformers, Mitrović/Bony/Jerome top underperformers. Added Learning Goals section to CLAUDE.md. S1–S4 committed.

---

## 2026-06-29 (cont.) — S5

`src/similarity.py`: minutes from StatsBomb `lineups` endpoint (more reliable than reconstructing from Starting XI + Substitution events — `lineups` tracks Tactical Shift position changes directly). Built per-90 event metrics for PL 2015/16 — 300 players at 900-min floor (118 Def / 104 Mid / 78 Fwd; GKs excluded). Hit sparse-column gotcha: `pass_goal_assist` missing from matches with zero assists — fixed with `_safe_bool_column`/`_safe_column` helpers. SkillCorner physical metrics derived from frame-to-frame position deltas; `min_observed_minutes=30` caps extrapolation at 3×. Confirmed zero player overlap between StatsBomb and SkillCorner datasets. Cached `data/player_per90_pl_2015_16.pkl`. S5 committed separately.

---

## 2026-06-29 (cont.) — S6

Added clustering to `similarity.py` and plotting to `visualisation.py`. Key design: **clustering per position group** (not across all outfield players — would just rediscover position). K=4 per group. Results: midfielder cluster Kanté/M'Vila/Gueye/Drinkwater (ball-winning destroyer, anchored by Kanté's title-winning Leicester season); Özil/Fàbregas/Lallana (creative playmaker, Özil's record-assist season); defender cluster Cresswell/Daniels/Bellerín/van Aanholt (overlapping full-backs). One-man defender cluster: Michail Antonio with absurd z-scores (+5.95 goals/90) — documented as labelling limitation, not a clustering bug. Notebook 03 runs clean.

---

## 2026-06-29 (cont.) — S7 + S8

**S7:** `find_similar_players()` — Euclidean distance in standardised space, within position group (continuous ranking, not just cluster membership). `plot_player_radar()` — mplsoccer Radar, axes at 5th-95th percentile. Hit StatsBomb quirk: Kanté stored as `N''Golo Kanté` (doubled apostrophe). Hit mplsoccer gotcha: `Radar.setup_axis` expects plain rectangular `Axes`, not polar (see `docs/ML_TOOLING.md`). Validated: Kanté → Gueye/Tioté/Coquelin/Fernando; Cresswell → Brunt/Davies/Sagna/Bertrand/Daniels; Kane → Vardy/Carroll/Ighalo/Defoe/Agüero. Added Theoretical Concepts Reference and Module C/PUP spec to ML_LEARNING_LOG.md.

**S8:** Replaced placeholder README.md with full project narrative — module framing, honest numbers, embedded PNGs, honest caveats (GBM non-win, Antonio cluster). S6/7/8 committed and pushed ("S6/7 - Radar charts + visuals + final polish + README"). All S1–S8 pushed.
