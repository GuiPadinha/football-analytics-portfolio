"""Named dataset definitions for the Player Evaluation Framework.

Replaces the magic `(competition_id, season_id, league_context)` tuples that were previously
scattered through the notebooks (e.g. `(9, 281, 'league')`). A named, self-documenting `Dataset`
makes the data subsets explicit, kills the positional-tuple ordering hazard, and gives one place
to record which competitions have StatsBomb 360 freeze-frame data available (used by the
360-context xG model — see the Phase 7 plan).

StatsBomb open-data competition/season ids come from `sb.competitions()`; the `has_360` flags
reflect the freeze-frame coverage published in StatsBomb's open-data repository.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    """A single StatsBomb open-data competition/season the project trains or tests on.

    Attributes:
        comp_id: StatsBomb competition id.
        season_id: StatsBomb season id.
        context: "league" or "tournament" — kept so league and tournament shots can be separated
            for the train/test split rationale (tournament football has a structurally different
            shot profile; see CLAUDE.md).
        label: human-readable name for charts, logs, and tables.
        has_360: whether StatsBomb publishes 360 freeze-frame data for this competition/season.
    """

    comp_id: int
    season_id: int
    context: str
    label: str
    has_360: bool = False


# --- League context (xG training) ---
LEVERKUSEN_2023_24 = Dataset(9, 281, "league", "Bayer Leverkusen 2023/24", has_360=True)
PL_2015_16 = Dataset(2, 27, "league", "Premier League 2015/16", has_360=False)

# --- Tournament context (xG test / out-of-distribution) ---
EURO_2024 = Dataset(55, 282, "tournament", "UEFA EURO 2024", has_360=True)

# --- Phase 4 candidate (freshly released free data with events + 360) ---
WOMENS_EURO_2025 = Dataset(53, 315, "tournament", "UEFA Women's EURO 2025", has_360=True)

# --- Phase 4 data expansion (2026-07-04, cached not yet wired into TRAIN_SETS/SIMILARITY_SET) ---
# StatsBomb's "La Liga" competition entry is misleading: verified by match/team count (not
# assumed from the name — see the Bundesliga/Ligue 1 single-team gotcha below), every season here
# except 2015/16 is actually Barcelona's own fixtures only — their well-known Messi-era open-data
# release, filed under the league rather than a separate "Barcelona" label. Guilherme is fine
# leaning into the Messi era (CONTEXT.md, 2026-07-04); pulling all 16 Barcelona seasons is cheap
# (866 matches total, ~15 min) since there's no "diminishing returns from redundant seasons"
# argument when every season is already non-overlapping single-club data, not a resampling of the
# same broad league.
BARCELONA_2004_05 = Dataset(11, 37, "league", "Barcelona 2004/05 (La Liga)", has_360=False)
BARCELONA_2005_06 = Dataset(11, 38, "league", "Barcelona 2005/06 (La Liga)", has_360=False)
BARCELONA_2006_07 = Dataset(11, 39, "league", "Barcelona 2006/07 (La Liga)", has_360=False)
BARCELONA_2007_08 = Dataset(11, 40, "league", "Barcelona 2007/08 (La Liga)", has_360=False)
BARCELONA_2008_09 = Dataset(11, 41, "league", "Barcelona 2008/09 (La Liga)", has_360=False)
BARCELONA_2009_10 = Dataset(11, 21, "league", "Barcelona 2009/10 (La Liga)", has_360=False)
BARCELONA_2010_11 = Dataset(11, 22, "league", "Barcelona 2010/11 (La Liga)", has_360=False)
BARCELONA_2011_12 = Dataset(11, 23, "league", "Barcelona 2011/12 (La Liga)", has_360=False)
BARCELONA_2012_13 = Dataset(11, 24, "league", "Barcelona 2012/13 (La Liga)", has_360=False)
BARCELONA_2013_14 = Dataset(11, 25, "league", "Barcelona 2013/14 (La Liga)", has_360=False)
BARCELONA_2014_15 = Dataset(11, 26, "league", "Barcelona 2014/15 (La Liga)", has_360=False)
BARCELONA_2016_17 = Dataset(11, 2, "league", "Barcelona 2016/17 (La Liga)", has_360=False)
BARCELONA_2017_18 = Dataset(11, 1, "league", "Barcelona 2017/18 (La Liga)", has_360=False)
BARCELONA_2018_19 = Dataset(11, 4, "league", "Barcelona 2018/19 (La Liga)", has_360=False)
BARCELONA_2019_20 = Dataset(11, 42, "league", "Barcelona 2019/20 (La Liga)", has_360=False)
BARCELONA_2020_21 = Dataset(11, 90, "league", "Barcelona 2020/21 (La Liga)", has_360=False)
BARCELONA_SEASONS = [
    BARCELONA_2004_05, BARCELONA_2005_06, BARCELONA_2006_07, BARCELONA_2007_08,
    BARCELONA_2008_09, BARCELONA_2009_10, BARCELONA_2010_11, BARCELONA_2011_12,
    BARCELONA_2012_13, BARCELONA_2013_14, BARCELONA_2014_15, BARCELONA_2016_17,
    BARCELONA_2017_18, BARCELONA_2018_19, BARCELONA_2019_20, BARCELONA_2020_21,
]

# The one genuine full 20-team La Liga season available (verified: 380 matches, 20 teams) — usable
# for Module B cross-league work, unlike the Barcelona-only seasons above.
LA_LIGA_2015_16_FULL = Dataset(11, 27, "league", "La Liga 2015/16 (full season)", has_360=False)

# Genuine full multi-team leagues (verified by match/team count, not just competition name —
# several "full competition" StatsBomb entries are actually single-team releases in disguise).
SERIE_A_2015_16 = Dataset(12, 27, "league", "Serie A 2015/16", has_360=False)
LIGUE_1_2015_16 = Dataset(7, 27, "league", "Ligue 1 2015/16", has_360=False)

# Women's football: full-season training data pairs with WOMENS_EURO_2025 as held-out test,
# mirroring the existing league-train/tournament-test structure for a fresh generalisation angle.
FRAUEN_BUNDESLIGA_2023_24 = Dataset(135, 281, "league", "Frauen Bundesliga 2023/24", has_360=False)
FA_WSL_2023_24 = Dataset(37, 281, "league", "FA Women's Super League 2023/24", has_360=False)

# Additional held-out tournament test contexts for Module A generalisation (Phase 4c).
COPA_AMERICA_2024 = Dataset(223, 282, "tournament", "Copa América 2024", has_360=False)
WORLD_CUP_2022 = Dataset(43, 106, "tournament", "FIFA World Cup 2022", has_360=True)
AFCON_2023 = Dataset(1267, 107, "tournament", "Africa Cup of Nations 2023", has_360=True)

# Events-only pull (Module A shape: xG training/test volume, no lineups needed).
PHASE_4_EVENTS_ONLY = BARCELONA_SEASONS + [
    LA_LIGA_2015_16_FULL, SERIE_A_2015_16, LIGUE_1_2015_16,
    COPA_AMERICA_2024, WORLD_CUP_2022, AFCON_2023,
]
# Events + lineups pull (Module B shape: per-90 features need minutes-played from lineups too).
PHASE_4_EVENTS_AND_LINEUPS = [FRAUEN_BUNDESLIGA_2023_24, FA_WSL_2023_24]


# Default xG split (Module A). League shots train; the held-out tournament tests generalisation.
TRAIN_SETS = [LEVERKUSEN_2023_24, PL_2015_16]
TEST_SETS = [EURO_2024]

# Datasets usable by the 360-context xG model (Phase 7) — only those with freeze-frame coverage.
SETS_WITH_360 = [ds for ds in (LEVERKUSEN_2023_24, PL_2015_16, EURO_2024) if ds.has_360]

# Primary similarity pool (Module B). One competition for now; widened in Phase 4.
SIMILARITY_SET = PL_2015_16
