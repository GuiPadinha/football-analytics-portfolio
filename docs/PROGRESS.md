# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-14 — Market value (Transfermarkt) + two-player Compare view

Continuing straight on from the previous session's three fixes: picked up two of the three
remaining backlog items named explicitly at the start of this pass (market-value integration,
side-by-side comparison view), deliberately stopping short of the third (a multi-season "player
career" page — needs new data pulls, out of scope here).

**Market value.** Researched `dcaribou/transfermarkt-datasets` properly before writing any
matching code — confirmed real network access (Python via the Bash tool has it; only Git Bash's
own shell-level `curl` doesn't, a refinement of an older, over-broad ML_TOOLING.md note), found the
real schema (`players`/`player_valuations` tables, dated valuation history), and hit a real `403`
from the hosting CDN that turned out to be User-Agent sniffing, not an auth problem (see
ML_TOOLING.md). Built `src/market_value.py`'s entity resolution — exact name match first, then a
token-subset fallback for "StatsBomb logs the full legal name, Transfermarkt the popular one." The
first version of that fallback (rank candidates by raw token count) was validated against real
data before shipping, not assumed correct, and it genuinely failed: it nearly matched Neymar to an
unrelated real player, "Júnior Santos," because common Portuguese surname tokens ("Santos",
"Junior") outscored the correct, much rarer "neymar" token under a naive count-based rule. Fixed
by weighting tokens by inverse corpus frequency instead of raw count — full account, including a
second bug (a name-construction particle like "de" winning a match by default when it was the only
candidate), in ML_LEARNING_LOG.md. Final result, verified against real 2015/16-era valuations for
every star player checked (Messi, Ronaldo, Neymar, Suárez, Kane, Agüero, Ibrahimović, Higuaín):
**1,215 of ~1,344 players matched (~90%)** across the four men's competitions in the pool — checked
directly, not assumed, that this Transfermarkt mirror has zero women's-football coverage at all,
so Frauen Bundesliga/FA WSL players are skipped outright rather than attempted-and-failed. Wired
into `app_data.build_app_artifacts` as a new `market_value.parquet` artifact (its own,
independently-rebuildable step — `with_market_value=False` skips it for an offline dev build) and
shown in three places: a player's own page, the "players like X" table, and a new Leaderboard
column (formatted with the same hand-formatted-text-column pattern the previous session's "None"
fix established, to avoid reintroducing that exact bug for a third nullable column).

**Compare players.** A new sidebar view — two independent player search/pick widgets (mirrors the
Player explorer's own pattern) pulling from the whole unfiltered pool, since a comparison across
positions/competitions is a reasonable thing to want (e.g. "is this expensive winger really worth
more than that cheap forward"). Market value and a Finishing panel always compare directly;
signature stats, an overlaid radar (new `visualisation.plot_player_radar_comparison`, built on
mplsoccer's own `draw_radar_compare` — no need to hand-roll a two-polygon radar), and a percentile
table only render when both picks share a position group, with a plain-language info message
explaining why when they don't.

**Verification.** Full `pytest` suite green (**86** — 75 unchanged + 11 new
`tests/test_market_value.py` cases, several reproducing the real matching bugs above as regression
tests: the Santos/Junior collision with a padded synthetic corpus matching the real one's token
frequencies, the particle-only false match, a genuine two-real-players ambiguity correctly left
unresolved). A scripted `AppTest` pass covered the Compare players view (same-position and
cross-position picks, checking for the right subheaders/info-message) and a market-value caption
render on a real player's page — zero exceptions. Playwright-over-Edge screenshots confirmed: a
real Messi-vs-Ronaldo comparison renders a correct blue/orange radar overlay and a "Cristiano
Ronaldo dos Santos Aveiro is valued €10.0M less than..." caption; a Forward-vs-Goalkeeper pick
correctly shows the cross-position info message and skips the radar section without an exception;
zero literal "None" text anywhere in either new feature; the Leaderboard's new Market value column
renders correctly (including a genuinely blank cell for the one La Liga forward whose name
matched two different real Transfermarkt players — left unresolved by design, not a bug). One real
screenshot false alarm on the way, immediately recognised rather than chased: a Leaderboard
screenshot taken right after a view switch showed stale Compare-players content underneath — the
exact documented Playwright timing artifact from a previous session (ML_TOOLING.md) — reshot with
a longer wait and it rendered cleanly. `python -m src.metrics` regenerates `metrics.json`
byte-identical throughout (this session's scope never touches the notebook/pipeline's narrow
single-competition numbers).

**Docs updated:** DATA.md (new "Transfermarkt Market Value Data" section, replacing the old
"flagged, not started" research-spike note; Cache Files table), MODULES.md (new Module B
paragraph), FRAMEWORK.md (two Out of Scope notes — modelling vs. displaying a market value is a
real distinction now, not just a future one), ML_LEARNING_LOG.md (the rarity-weighting entity-
resolution lesson), ML_TOOLING.md (the R2/User-Agent gotcha, and the Git-Bash-vs-Python-network
clarification), ROADMAP.md (Phase 9 list), PITCH.md (demo script, key numbers, roadmap, "why isn't
X done" sections), PRODUCT_SPEC.md (new dated section), app.py's own "About & Roadmap" copy (Data
used / How to use / What's shipped sections).

---

## Commit Status

Verified against `git log`/`git status` 2026-07-14. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit on `origin/main`: `067a9d2` (goalkeeper clustering, cross-league
normalisation, Leaderboard "None" fix). The market value + Compare players entry above is
**complete but not yet committed** — working tree has uncommitted changes as of this write-up (per
CLAUDE.md's Session Workflow, only commit when explicitly asked). Entries through 2026-07-13
(cont. 6) moved to [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md) to keep this file under 150 lines.
