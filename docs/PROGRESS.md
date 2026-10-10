# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1 through 2026-10-02): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-10-10 — Redesign step 1b: the pages (in stages)

Stages, one commit + push each: **A** view models (done) · B Player page + top navigation + theme ·
C Compare · D Home, Leaderboard, How it works · E docs.
- **A. `src/profile.py`:** `prepare_pool` (adds each player's game, ranks every position group
  once), `build_player_profile` (strength/weakness bars, finishing or saves, price, men's and
  women's top-5 lookalikes, the short version) and `build_compare_view` (verdict + one row per
  stat). Pure functions, tested on the real tables (`tests/test_profile.py`); a profile builds in
  ~0.05 s.
- **A. `src/findings.py`:** the Home cards are computed, not typed (the mockup still said six
  leagues). Biggest over/under-performer against their chances (Agüero +6.5, Jerome −4.2), the
  share of valued men with a half-price top-3 lookalike (94% of 282 at €10M+; stated as a fact
  about the pool with its caveat, because "the biggest gap" picks Ronaldo vs. Bony), and the most
  valuable man whose closest woman has him as her closest man (Agüero ↔ Khadija Shaw, both Man
  City). `python -m src.findings` writes `app_data/findings.json` in ~16 s, and `src.app_data`
  calls it at the end of a rebuild.
- **B. The new shell, Home and Players pages.** `app.py` is now just the page frame and a top
  `st.navigation` (Home, Players, Compare, Leaderboard, How it works); each page is a script under
  `views/`. `views/components.py` holds the stylesheet (the mockup's palette, also in
  `.streamlit/config.toml`), the escaped HTML builders and a native Altair shot map, cropped to
  where the player shoots from. `views/data.py` caches the pool. Home shows the four computed
  cards; Players is the three questions, with men's and women's lookalike tabs (own game first) and
  a "similar style is not the same level" caveat next to prices. The old radar, percentile chart,
  sidebar filters and Euclidean/σ captions are gone from player pages. Compare, Leaderboard and
  How it works still run the old code, moved verbatim to `views/legacy.py` until C and D.
  Checked in a real browser (Edge via Playwright): a star, a keeper and a women's player. The smoke
  tests were rewritten for the new pages (15 AppTest cases, `tests/test_components.py`).
- Small: `format_rate` is public (two decimals under 1: "0.38 per 90"), and the label reads
  "Non-Penalty Goals".

---

## 2026-10-06 — Redesign step 1a: the rule-based text

Guilherme approved the plan, plus the league-adjusted ranking below ("go ahead, log all that").
- **`src/narrative.py` (new).** The player page's short version: standout stats, then finishing
  (or saves), then price. Without a price (women's football, unmatched men) the closest match in
  each game takes the last slot. Compare's verdict: closeness rank, each side's leads, keepers'
  save %, then the price gap. Every threshold is a named constant calibrated on the real pool.
- **`similarity.py`:** `rank_matches` is the full ranking (`find_similar_players` is now its top n,
  output unchanged). `league_adjusted_percentiles` is the new basis for "top N%".
  `pair_closeness` is Compare's rank, in the right space for each position pair. Also
  `config.GENDER_BY_COMPETITION`, `presentation.ordinal` and `presentation.popular_name`.
- **Decisions, each measured first** (ML_LEARNING_LOG.md has the numbers):
  - Percentiles rank league standing, not raw rates (a ~6-point mean shift, up to ~50).
  - Finishing is quoted as exact odds for an average finisher ("about one season in 22").
  - Closeness is a rank, not a distance cutoff.
  - Mixed-position pairs get their own space, because `_lz` is position-relative.
  - A lead needs both a league-SD gap and a visible raw gap.
- **Checked on 16 players and 8 pairs:**
  - Mahrez reads almost word for word like the mockup.
  - Benzema–Pajor: "closest match among 194 women's forwards".
  - Also checked: keepers, women, players with no xG, Kanté ("too few chances to judge"), and a
    keeper against an outfielder (refused).
  - Reading the output changed three rules: leads must be visible in the raw numbers, all-below-
    median keepers are "quiet keepers", and women get the cross-game sentence.
- **Verified:** 233 tests pass, and the pipeline's `metrics.json`, PNGs and manifest are
  byte-identical. `app.py` is untouched, so the live app doesn't change until step 1b.
- **Open for 1b:**
  - 159 players have no nickname and a long legal name ("Mary Alexandra Earps", Liga F double
    surnames).
  - The page must say "similar style, not the same level" next to prices.

---

## 2026-10-03 (cont.) — Product rethink; three more women's leagues

Guilherme, after seeing the redeployed app: lots of numbers, no insights, cheap-looking UI,
jargon (σ, "Euclidean distance"), legal names, and no reason to block midfielder-vs-forward
comparisons. Agreed plan, in order:
1. **More data (done here).** Checked what exists before deciding: StatsBomb open data has no
   further full men's league seasons (Bundesliga 15/16 and Ligue 1 21/22–22/23 are one club's 34
   games each). It does have three unused full women's seasons. **Liga F 2023/24, Serie A Women
   2023/24 and NWSL 2023** are now in `SIMILARITY_SETS`: 9 competitions, **2,170 players** (168
   keepers), team counts checked in `test_app_data.py`. Download + rebuild took 17.5 min, and
   market values are unchanged. Keeper silhouette is now 0.214 at K=2 and 0.198 at K=4 (outfield
   0.133–0.141 at K=4). Larger men's expansion = Wyscout 2017/18 (Phase 4e), and Kaggle's "all
   World Cups" sets are results-only (already noted in ROADMAP 4e on 10-01).
2. **Redesign** (next): Streamlit kept. A mockup (Home with findings, a three-question player
   page, Compare with a verdict) was approved as the direction. Lookalikes come in separate men's
   and women's top-5 lists, both ways. The short version and verdict sentences will be generated
   by tested rules, not an LLM.
3. Wyscout 2017/18, then Phase 5a.

---

## 2026-10-03 — Live app moved to Python 3.14

Guilherme deleted the 3.10 app and redeployed. The new app crashed with `ModuleNotFoundError:
matplotlib`: its Python was the Cloud default, 3.14, and the pinned numpy 2.2.6 has no 3.14 wheel,
so nothing beyond Streamlit's own packages got installed (ML_TOOLING.md). Guilherme asked why not
just use 3.14. No reason not to: it's the Cloud default and supported until 2030.
- numpy 2.2.6 → 2.3.5, the only pin without 3.14 wheels. Every other runtime pin has them.
- Verified on 3.14.7 (local venv) and 3.12: 171 tests pass on both. The app's tests also pass
  with only `requirements.txt` installed, as on the Cloud. Pipeline outputs are identical across
  the two versions. `metrics.json` is unchanged, while `feature_importance.png` moved in the third
  decimal from the numpy bump (ML_LEARNING_LOG.md).
- CI matrix is now 3.12 (local) + 3.14 (Cloud), with the `app-runtime` job on 3.14. The runner stays
  pinned to `ubuntu-24.04`, so the image changes only on purpose. 3.10 references updated in the
  docs.

**Keepers: only shots on target count** (Guilherme's call). The "shots faced in total" figure next to
save % is gone. A save of a shot going wide ("Shot Saved Off Target") no longer counts as a save,
because StatsBomb's own shot outcome calls that shot off target: 166 saves across 90 keepers, at
most 5 each. Median save % 70.1% → 69.8%. Outfield data and market values are unchanged. 12 of 123
keepers moved archetype (soft continuum). Keeper silhouette 0.238 at K=2 (was 0.237), 0.187 at
K=4 (unchanged). The rebuilt xG tables differed only by float noise from the numpy bump, so the
committed files were kept.

**Market value: Luis Suárez and 158 more** (Guilherme asked "what's happening to Suárez?").
Transfermarkt has two "Luis Suárez" profiles, and the matcher dropped any name with two
candidates before the club check could tell them apart.
- StatsBomb's lineups carry each player's popular name (`player_nickname`: "Koke", "Dani Alves",
  "Luis Suárez"), which is how Transfermarkt names players. It now flows into the per-90 tables
  as `nickname`.
- Matching is now two plain steps. `find_name_candidates` lists every Transfermarkt player matching
  the nickname or the full name, exactly or by distinctive words. `keep_candidates_at_the_right_club`
  keeps the one valued at the player's club that season (no candidate or two left = blank).
  Letters like Ł/Đ/ð are transliterated the way Transfermarkt writes them. The position tiebreak
  changed nothing any more and was removed.
- 1,168 → **1,327 of 1,347 (~99%)**: no existing match changed, and all 159 new ones were reviewed by
  hand (Suárez €90M, Koke, Isco, Fàbregas, David Silva, Dani Alves, Pepe, Mikel...). 20 stay
  blank (spellings with no shared word, bare common names like "Nacho", parent-club loanees).
- The pipeline's similarity cache rebuilt itself for the new column. `metrics.json`, PNGs and the
  manifest are byte-identical, and per-90 values and clusters are unchanged.

**Phase 5a heads-up, measured:** the Finishing panel's in-sample xG vs. out-of-fold xG moves a PL
player's goals − xG by 0.02 goals on average (max 0.20); the top-10 overperformers are the same
set. 5a should still use out-of-fold xG (ML_LEARNING_LOG.md).

---

## 2026-10-02 → 10-03 — Deep audit: three shipped data bugs, then hardening

Guilherme wasn't confident two health checks had found everything and asked for a ground-up
audit until there's a clear green light. Every `src/` module, `app.py`, the tests, CI, configs and
docs were read, and each suspicion was checked against real data before acting.

**Wrong data the live app was showing (fixed, with tests that read the shipped tables):**
- *Goalkeeper save %:* median 38% instead of ~70%. StatsBomb's "Shot Faced" is only the remainder
  (off target/blocked), not all shots. Shots faced, saves (incl. penalty saves), goals conceded
  (incl. penalties) and save % are now counted correctly, verified on 150 matches. Shots faced
  became display-only (it measures the defence), like outfield `goals`.
- *Ligue 1 had 21 teams:* "Marseille"/"Olympique de Marseille" and "Caen"/"Stade Malherbe Caen"
  split players' seasons (Mandanda appeared twice). Team names are now mapped onto each match
  sheet; the pool grew from 1,635 to 1,638 players, and from 124 to 123 keepers.
- *Market value attached to the wrong people:* Dani Alves, Koke, Gabi, Danilo, Fernandinho, Jonny
  Evans, David Silva (€100k from a 2024 valuation) and more. A club check now requires
  Transfermarkt to place the player at the StatsBomb team's club within 12 months of the season:
  76 of 1,244 matches removed, 1,168 kept (~87%), all stars still correct.

**Also fixed:**
- *"Key Passes" label:* StatsBomb flags a pass that set up a goal as an assist and never also as
  a shot assist (0 overlaps in 120 matches), so the count excludes assists (Özil: 123 + 19). The
  feature stays as is: disjoint is cleaner for clustering. The label now reads "Key Passes (excl.
  Assists)" in the app and on the radar; only `player_radar_examples.png` changed.
- A page crash when fewer than three radar axes were selected. Goals Conceded is now drawn
  reversed on the radar.
- Cache writes are atomic (`net.write_atomically`). The manifest now pins the six similarity
  leagues too: 13 datasets, 2,109 matches.
- The game-state feature walks events in StatsBomb's own order; no shot was affected.
- Doc-lint now also checks the app numbers (players, keepers, market values, match rate) against
  `app_data/`.
- Removed dead config (`PHASE_4_*` lists) and a dead tuple branch; one home for `CLUSTER_K` and
  the outfield group list; shared GBM settings; corrected docstrings (CV "random slices",
  `--force` "re-pull", "offline" builds) and six app statements wrongly saying Leverkusen
  players have xG.
- Checked and left alone: CV scheme (mean 0.783 under every scheme, logged), dependency audit (no
  known vulnerabilities), statsbombpy row order (no impact).

**Verified:** 170 tests pass. The pipeline run gives `metrics.json` and all 9 PNGs byte-identical
(25 s now). `app_data/` was rebuilt with the fixes, and the notebooks re-executed.

---

## Commit Status

Git CLI is used directly (see CLAUDE.md's Session Workflow). This section is only a pointer; check
`git log`/`git status` for the real state. Since 2026-10-01 each phase of the health-check plan is
committed and pushed on its own (Guilherme's request), so `origin/main` tracks the latest
finished phase.
