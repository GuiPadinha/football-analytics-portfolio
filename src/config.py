"""Named dataset definitions for the Player Evaluation Framework.

Replaces the magic `(competition_id, season_id, league_context)` tuples that were previously
scattered through the notebooks (e.g. `(9, 281, 'league')`). A named, self-documenting `Dataset`
makes the data subsets explicit, kills the positional-tuple ordering hazard, and gives one place
to record which competitions have StatsBomb 360 freeze-frame data available (used by the
360-context xG model — see the Phase 3 plan).

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


# Default xG split (Module A). League shots train; the held-out tournament tests generalisation.
TRAIN_SETS = [LEVERKUSEN_2023_24, PL_2015_16]
TEST_SETS = [EURO_2024]

# Datasets usable by the 360-context xG model (Phase 3) — only those with freeze-frame coverage.
SETS_WITH_360 = [ds for ds in (LEVERKUSEN_2023_24, PL_2015_16, EURO_2024) if ds.has_360]

# Primary similarity pool (Module B). One competition for now; widened in Phase 4.
SIMILARITY_SET = PL_2015_16
