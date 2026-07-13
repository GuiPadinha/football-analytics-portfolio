# Progress Log — Recent Sessions

→ [CLAUDE.md](../CLAUDE.md) | Historical (S1–S8, Phase 0–2): [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md)

Add new entries at the top. Move old entries to PROGRESS_ARCHIVE.md when this file exceeds 150 lines.

---

## 2026-07-13 — Pitch-prep pass: app "About / how to use" banner, market-value data spike

Guilherme pitched the project to a colleague today; asked to review the backlog, prep pitch/
roadmap talking points, and make the live app more self-explanatory (a description of the
framework + how to use it, "máximo de informação possível") before the demo.

**Backlog reviewed, nothing shipped from it this session** (all three items are still open, on
purpose — see `PRODUCT_SPEC.md`'s "Backlog from 2026-07-06 feedback"): goalkeepers not wired into
the app, "Under the hood" methodology expander still flagged low-value/on hold, one cosmetic
expander-state follow-up from the drill-down work. Talking points and a demo script (leaderboard →
player explorer → similar-player click-through → finishing panel → credibility numbers →
roadmap) were prepared directly in chat, not saved as a repo doc — a one-off presentation aid, not
project documentation that needs maintaining.

**`app.py` gained a main-pane "About" banner**, rendered above both views (Player explorer and
Leaderboard) right after the sidebar title block: a one-line framework summary, a two-column
explanation of the two lenses (similarity/scouting, xG/valuation), a 4-tile `st.metric` row (xG
ROC-AUC, competition count, player count, test count — reusing the same metric-card idiom already
used for signature stats, not a new pattern), an expanded-by-default "How to use this app" 7-step
guide, and a GitHub link. Deliberately did **not** touch the existing "Under the hood" expander —
still explicitly on hold per the 2026-07-06 feedback backlog, and this pass's ask (more *framework*
explanation) doesn't supersede that hold, which was about *methodology plot* redesign specifically.

Verified live via `streamlit run app.py` + the Playwright-over-Edge recipe (`ML_TOOLING.md`):
screenshotted both views. First Leaderboard screenshot showed leaderboard content *and* stale
Player-explorer content both on screen at once — not a real bug, confirmed by re-shooting with a
longer post-click wait (4s vs. 2s): Streamlit doesn't prune trailing elements from the previous run
until the new run fully finishes, so a screenshot taken mid-transition can catch old + new content
overlapping. Worth remembering next time a click-driven verification looks inconsistent — wait
longer before concluding it's a product bug.

**Mid-session ask: could the app show market value next to similarity matches?** Researched rather
than guessed. Finding: a maintained, weekly-refreshed open dataset
([dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets), also on
Kaggle) has a dated `player_valuations` table — so the data itself isn't the blocker, contrary to
the instinctive assumption that this would need scraping from scratch. The real cost is matching
StatsBomb player identities to Transfermarkt's (no shared ID — a name-resolution problem: accents,
birth-name-vs-shirt-name, same-name collisions) plus picking the right valuation snapshot per
season and a ToS caveat (the upstream dataset is itself built by scraping, so legality is inherited
not cleared). Real engineering, not a config line — logged as a scoped future item, not built now:
see [DATA.md](DATA.md#market-value-transfermarkt--flagged-2026-07-13-not-started) for the full
assessment and [ROADMAP.md](ROADMAP.md) Phase 9 for the pointer.

No `src/`/model/test changes this session — presentation and docs only. Full `pytest` suite
untouched (still 72 green, not rerun since nothing in `src/` changed).

---

## 2026-07-13 (cont.) — "About & Roadmap" promoted to its own tab; headline numbers refactored off decimals

Follow-up feedback on the same day's pitch-prep pass, three asks: (1) the S1–S9 vs. Phase 0–9
numbering was genuinely confusing — clarified directly in `docs/ROADMAP.md` (a note right above
the S1–S9 table) rather than just re-explained in chat, since the next person to open that file
hits the same confusion; also wrote `docs/PITCH.md` so the pitch script has an actual file path.
(2) Keep "Under the hood" but make it less prominent, with suggestions for new sections. (3) A
feasibility read on doing this now vs. next session — answered "there's time, do it," plus:
promote the suggested "roadmap teaser" into its own full tab (an "About-me"-style project page),
and refactor every headline stat off decimal ML scores (ROC-AUC, silhouette) onto whole-number
counts — "I need to be able to justify these numbers," decimals only where the methodology
explaining them lives.

**`app.py` restructure:** the sidebar `view` radio gains a third option, **"About & Roadmap"**
(`render_about_and_roadmap`), replacing the previous always-on-every-page main-pane banner (which
repeated the same essay above both the Player explorer and Leaderboard views). That banner is now
a one-line caption pointing at the new tab instead. The new tab holds: the two-lens framework
explanation, a "What's been built" stat row, the FRAMEWORK.md worked example ("how the two lenses
combine"), the "How to use this app" guide, a plain-language "what's shipped / what's next"
summary, and a collapsed **"Methodology"** expander — the only place decimal stats live now,
each one explained inline (what ROC-AUC means, the baseline ladder, the per-tournament
generalisation table + `plot_xg_generalisation_bar` chart, i.e. the app's first use of that chart —
it existed in `metrics.json`/`src/visualisation.py` since Phase 4c but was never wired into the UI
before). The per-player "Under the hood" expander (bottom of the Player explorer page) is slimmed
to a one-line pointer at the new tab plus the one thing genuinely specific to that page: the
current position group's live silhouette curve.

**Headline numbers are now whole counts, not decimals:** "What's been built" shows Competitions
(6), Players in the pool (1,511), Shots evaluated (15,528 = 10,824 trained + 4,704 held-out across
4 tournaments), Tournaments tested on (4) — no ROC-AUC/silhouette figure appears outside the
Methodology expander anywhere in the app. `docs/PITCH.md` refactored the same way: a "Key numbers
to lead with" whole-number section, and the decimal ROC-AUC/generalisation-range numbers moved to
a new "Methodology backup — only if asked to justify the model" section.

**Backlog-only, not built** (explicit ask): a side-by-side two-player comparison view — logged in
`ROADMAP.md`'s Phase 9 opportunistic list, no code.

Verified live via `streamlit run app.py` + Playwright-over-Edge across all three views. Hit the
same stale-trailing-content timing artifact as the earlier pass today (switching to "About &
Roadmap" right after page load showed old Player-explorer content — shot map, old "Under the hood"
— still rendered below the new tab's content); confirmed harmless by re-shooting with a longer wait
(6s) both from a warm session and a fresh page load — clean either way. Full `pytest` suite still
**72 green** (no `src/` changes, only new imports of already-tested `visualisation.plot_xg_generalisation_bar`).

---

## 2026-07-13 (cont. 2) — Doc-hygiene pass: INITIATIVE.md's Log was duplicating PROGRESS_ARCHIVE.md

Guilherme flagged, before committing, that `INITIATIVE.md` seemed to carry the project's logs "in
full" and asked whether that was too heavy — he remembered a separate history file for that (there
isn't one by that name; he meant `PROGRESS_ARCHIVE.md`). Checked rather than assumed: `INITIATIVE.md`
was 203 lines, its "Log" section repeating the same milestones as full paragraphs already fully
covered, in more detail, in `PROGRESS_ARCHIVE.md` (which has no size cap of its own and was already
852 lines). Confirmed every dated INITIATIVE.md log entry has a matching, more detailed entry in
PROGRESS_ARCHIVE.md before trimming, so nothing was lost — genuine duplication, not two views of
different information.

**Trimmed `INITIATIVE.md`'s Log to a one-line-per-milestone index** (203 → 89 lines), each line
pointing at PROGRESS.md/PROGRESS_ARCHIVE.md for the narrative. Matches the file's own stated
purpose ("this is the where-are-we tracker," not a second history) and removes a two-logs-must-
stay-in-sync-by-hand failure mode.

Also asked to make sure all the relevant `.md` files were actually current, not just the ones
directly asked about — checked each:
- **`docs/ML_TOOLING.md`**: a real gap. This session hit the same Playwright-view-switch
  stale-content timing artifact twice (Leaderboard, then About & Roadmap) but it had only been
  written up in PROGRESS.md's narrative, not logged as the reusable tooling gotcha it actually is.
  Added a new entry (placed next to the existing Playwright-over-Edge recipe).
- **`ML_LEARNING_LOG.md`**: nothing to add — this session touched no `src/` code, no model, no
  data; that log is for modelling/data gotchas specifically, and there weren't any.
- **`CLAUDE.md`**: the "Next (open backlog)" line still called the "Under the hood" rework an open
  item — stale as of this session's own earlier work. Updated to mark it done, added the
  2026-07-13 pass to the Active Initiative narrative, and fixed two unrelated small drifts noticed
  while in there: the Repository Layout's test count said "61" (actually 72 — this number is
  deliberately excluded from the metrics.json doc-lint check per Phase 3b, so it can drift
  silently), and its one-line descriptions of `ROADMAP.md`/`PROGRESS.md`/`PROGRESS_ARCHIVE.md` were
  stale summaries from when those files held different content. Also added the new `PITCH.md` to
  the layout listing.
- **`docs/PRODUCT_SPEC.md`**: the "Under the hood... flagged as low-value, under review" backlog
  bullet was the exact item this session's earlier pass had already shipped — marked
  `[DONE 2026-07-13]` with what actually got built, matching the `[DONE ...]` convention the other
  backlog bullets in that same list already use.

No `src/`/test changes; full `pytest` suite re-run after all doc edits, still **72 green** (docs
can't break tests, verified rather than assumed).

---

## Commit Status

Verified against `git log`/`git status` 2026-07-13. Git CLI is used directly (see CLAUDE.md's
Session Workflow) — this section is a lightweight pointer, not a substitute for `git log`/`git
status`. Latest commit: `3c62c2d` (penalty info + clickable similar-player drill-down). This
session's changes (`app.py`'s "About & Roadmap" tab + headline-number refactor, `docs/PITCH.md`
(new), plus a doc-hygiene pass across `INITIATIVE.md`/`CLAUDE.md`/`PRODUCT_SPEC.md`/`ML_TOOLING.md`/
`docs/DATA.md`/`docs/ROADMAP.md`, and this file) are presentation/docs-only and **not yet
committed** — Guilherme to review before committing. Older entries (2026-07-08 through 2026-07-09
cont. 5) moved to [PROGRESS_ARCHIVE.md](PROGRESS_ARCHIVE.md) to keep this file under 150 lines.
