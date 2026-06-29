"""Data ingestion for the Player Evaluation Framework.

Wraps statsbombpy (event data, open data, no API key required) and kloppy's
SkillCorner loader (open broadcast tracking data) behind a small, consistent
interface used across the xG and player similarity modules.
"""

from statsbombpy import sb
from kloppy import skillcorner


def load_competitions():
    """Return all competitions available in StatsBomb open data.

    Returns:
        pandas.DataFrame: one row per competition/season.
    """
    return sb.competitions()


def load_matches(competition_id, season_id):
    """Return match metadata for a given competition and season.

    Args:
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.

    Returns:
        pandas.DataFrame: one row per match.
    """
    return sb.matches(competition_id=competition_id, season_id=season_id)


def load_events(match_id):
    """Return granular event data (shots, passes, pressures, etc.) for a match.

    Args:
        match_id (int): StatsBomb match id.

    Returns:
        pandas.DataFrame: one row per event.
    """
    return sb.events(match_id=match_id)


def load_lineups(match_id):
    """Return player lineups for a match.

    Args:
        match_id (int): StatsBomb match id.

    Returns:
        dict[str, pandas.DataFrame]: lineup per team, keyed by team name.
    """
    return sb.lineups(match_id=match_id)


def load_360_frames(match_id):
    """Return 360 freeze-frame data (visible player positions per event) for a match.

    Only available for a subset of StatsBomb matches.

    Args:
        match_id (int): StatsBomb match id.

    Returns:
        pandas.DataFrame: one row per freeze frame.
    """
    return sb.frames(match_id=match_id)


def load_skillcorner_tracking(match_id):
    """Return SkillCorner open broadcast tracking data for a match via kloppy.

    Args:
        match_id (int): SkillCorner open data match id.

    Returns:
        kloppy.domain.TrackingDataset: tracking frames for the match.
    """
    return skillcorner.load_open_data(match_id=match_id)
