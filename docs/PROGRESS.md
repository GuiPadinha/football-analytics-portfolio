# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-07-14): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-10-02 (cont.) — Re-audit of the health check

Guilherme asked for a last check for loose ends before moving on. Every 2026-09-30 finding was
re-verified against the repo.
- **Closed, verified:** every item except the Cloud redeploy on 3.12, which is still pending and
  comes next. Full suite 147 passed. Every relative link and `#L` anchor resolves except two in the
  archive (below). README PNGs are tracked; CI is on actions v7 + `ubuntu-24.04`; the requirements
  split is in place. The Suárez correction is in DATA.md. `app_data/` rebuilt on 3.12 gives
  identical frames, so the committed 3.10 files were kept (diff ≤ 9e-16, see ML_LEARNING_LOG.md).
- **Killed:** a leftover `streamlit run` (port 8599, Python 3.10, `0.0.0.0`) from the 10-01
  browser check had been running for a day. No local Streamlit process is left (ML_TOOLING.md).
- **New, logged in ML_TOOLING.md:** this VS Code session still resolved `python` to 3.10.7, because
  it predates the PATH change (fix: restart VS Code). A form-feed byte had corrupted a path in
  ML_TOOLING.md's uv entry; it is repaired and the way it happened is noted.
- **New, logged as ROADMAP.md Phase 9 "Re-audit fixes":**
  - the similarity-table cache only checks that the file exists (latent; no number is wrong today);
  - the doc-lint covers 9 xG numbers, not the per-tournament AUCs or the silhouettes;
  - `src.app_data` takes ~10.6 min, re-reads events twice per competition, and isn't part of
    the pipeline;
  - three restructure leftovers (Makefile/INITIATIVE mentions, two dead archive links);
  - a list of the docs that need updating once the redeploy happens.

**Fixed the same day** (Guilherme: fix rather than just log; one commit + push each):
- *Similarity cache:* `pipeline.build_similarity_table` now rebuilds when the cached columns differ
  from the new `similarity.PER90_TABLE_COLUMNS`, which is also what `build_player_per90_features`
  returns. The real pipeline run on 3.12 detected the stale July pickle and rebuilt it on its
  own. `metrics.json`, the manifest and all 9 PNGs came out byte-identical. +1 test.
- *Doc-lint:* now also requires the six per-tournament AUCs in README/CLAUDE/MODULES and the
  silhouette range ("0.22–0.26") in CLAUDE/MODULES/PITCH. A deliberately drifted AUC is caught.

---

## 2026-09-30 → 10-02 — Health check after a 2.5-month gap, then a six-phase fix-up

Full detail (every finding, number and bug) is in [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)
under the same dates. One commit + push per item, CI green throughout.

- **Health check (09-30).** Read every doc and reviewed the code; re-ran the notebooks and checked
  CI, the live app and the upstream sources. Results were logged before any fix.
- **Phase 1, HTTPS + ingestion.** Avast rotated its root cert, so Python HTTPS was dead. New
  `src/net.py` routes downloads through the OS trust store (`truststore`) and adds
  retry/backoff. pip was upgraded (22 → 26). The lost certifi gotcha was recovered into
  ML_TOOLING.md.
- **Phase 2, quick wins.**
  - The Leaderboard is numeric again via `st.dataframe(placeholder="")`; Streamlit #7360 had been
    fixed upstream since 2025-11.
  - README images were committed; they had been broken on GitHub because `outputs/` was ignored.
  - The Module B narrative was rewritten for the 11-feature clusters. The Antonio one-man cluster
    no longer exists, but he's still the most extreme defender.
  - CI actions bumped to v7; plotly dropped.
- **Phase 3, `app.py`.** Text helpers moved to `src/presentation.py`, the Player explorer became a
  function, and `tests/test_presentation.py` + `tests/test_app_smoke.py` (AppTest) were added. A
  nested-bold blurb bug was caught along the way.
- **Phase 4, Python 3.12.** Requirements split into runtime vs. dev; statsbombpy/kloppy are now
  lazy-imported. CI runs a 3.10/3.12 matrix plus an `app-runtime` job. The local interpreter is
  3.12.10 (10-02), and the pipeline reproduces byte-for-byte on 3.12. *The Streamlit Cloud
  redeploy on 3.12 is still open* (approved by Guilherme, next session).
- **Phase 5, ingestion.**
  - A stale-cache bug was fixed (caches now check competition ids).
  - Women's EURO 2025 + Women's World Cup 2023 were wired in (0.763 / 0.777, no women's
    under-prediction).
  - "EURO 2024 is the floor" was corrected: it was false, because Copa América is lower.
  - The shot map was made deterministic (mplsoccer's grass texture used the global RNG).
  - Phase 4e (new sources + 360) was pinned.
- **Phase 6, declutter + docs.** `.vscode` untracked; Makefile and .claudeignore removed;
  conftest/ML_LEARNING_LOG moved; INITIATIVE merged into ROADMAP; PRODUCT_SPEC rewritten as the
  app's spec (458 → 168 lines); CLAUDE.md slimmed (218 → 154 lines); README docs map added; Phase
  9 regrouped.
- **Also logged:** World Cup 2026 is not in StatsBomb open data yet; the CC0 match-level dataset
  has no shot coordinates. paolomagni/football-platform is noted as a DE-showcase reference. The
  Luis Suárez market-value tiebreak and the sleeping live demo went to the backlog.

**Next:** (1) redeploy the Cloud app on Python 3.12, then drop 3.10 from CI; (2) Phase 5a,
uncertainty on goals − xG.

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
