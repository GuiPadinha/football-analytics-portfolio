"""Data ingestion for the Player Evaluation Framework.

Wraps statsbombpy (event data, open data, no API key required) and kloppy's
SkillCorner loader (open broadcast tracking data) behind a small, consistent
interface used across the xG and player similarity modules.

Per-match StatsBomb pulls (events, lineups, 360) are cached to disk by match id.
StatsBomb open data is immutable, so a match's data never changes once cached —
this turns `build_training_dataset`'s full-season pull from an ~8-minute,
all-or-nothing network operation into an incremental, crash-resilient one
(re-running after a failure reuses everything already fetched, and adding a new
season doesn't re-pull existing ones). Caching uses pickle rather than parquet
on purpose: StatsBomb events carry nested list/dict columns (locations, freeze
frames) and lineups is a dict of DataFrames — both round-trip cleanly through
pickle but not through columnar parquet.

Every network call goes through `src.net`: TLS is verified against the OS certificate store
(`use_os_trust_store`, called once at import) and transient failures (429, 5xx, dropped
connections) are retried with backoff (`with_retries`) — see that module for why.
"""

import os
import pickle
from pathlib import Path

import pandas as pd

from src.net import use_os_trust_store, with_retries

use_os_trust_store()

# data/ is gitignored; by default the cache lives under it so cached pulls never get committed.
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR_ENV_VAR = "FAP_CACHE_DIR"


def resolve_cache_dir(environ=os.environ):
    """Where the per-match cache lives: `$FAP_CACHE_DIR` if set, else `data/cache`.

    An override because the default can be a bad place for ~8.5 GB of pickles: this clone sits
    inside OneDrive, which kept syncing every cached match to the cloud. A fresh clone without the
    variable behaves exactly as before.

    Args:
        environ (Mapping[str, str]): environment to read; injectable for tests.

    Returns:
        Path: the cache directory (not created here; `_disk_cached` creates it on first write).
    """
    override = environ.get(CACHE_DIR_ENV_VAR, "").strip()
    return Path(override) if override else DEFAULT_CACHE_DIR


CACHE_DIR = resolve_cache_dir()

_download_notice_shown = False


def _announce_first_download():
    """Say where downloads are going, once per process, on the first cache miss.

    A cache miss is expected on a fresh clone. But it is also what a process sees when it can't
    find the real cache, e.g. one started before `FAP_CACHE_DIR` was set, which would otherwise
    re-download gigabytes into the default folder without a word.
    """
    global _download_notice_shown
    if not _download_notice_shown:
        print(f"Downloading uncached StatsBomb matches into {CACHE_DIR} "
              f"(set {CACHE_DIR_ENV_VAR} to use another folder)")
        _download_notice_shown = True


def _statsbomb():
    """statsbombpy's `sb` API, imported on first use rather than at module import.

    Lazy on purpose: `similarity` (and through it the deployed app) imports this module for the
    sparse-column helpers below but never downloads anything, so the app's runtime requirements
    don't need statsbombpy or kloppy at all (requirements.txt vs. requirements-dev.txt).
    """
    from statsbombpy import sb

    return sb


def safe_bool_column(df, column):
    """Return `df[column]` as booleans, or all-False if the column is absent.

    statsbombpy only includes a column in a match's events DataFrame if at least one event in
    that match actually has it set (e.g. `pass_goal_assist` is missing entirely from matches with
    zero assists, `shot_first_time` from a match with zero first-time shots) — sparse flag columns
    can't be accessed directly without risking a KeyError on an otherwise ordinary match. Shared
    by `features.py` and `similarity.py`, both of which hit this on different sparse columns.
    """
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return df[column].eq(True)


def safe_column(df, column, default=None):
    """Return `df[column]`, or an all-`default` Series if the column is absent.

    Same sparse-column issue as `safe_bool_column`, for non-boolean fields (e.g. `pass_outcome`
    is absent entirely from a match with zero incomplete passes, `duel_type` from a match with
    zero duels of that type recorded).
    """
    if column not in df.columns:
        return pd.Series(default, index=df.index)
    return df[column]


def _disk_cached(kind, match_id, producer, use_cache=True):
    """Return `producer()`'s result, reading from / writing to a per-match pickle cache.

    Args:
        kind (str): cache namespace ("events", "lineups", "360"), used in the filename.
        match_id (int): StatsBomb match id, the cache key.
        producer (callable): zero-arg function that fetches the data if not cached — retried
            on transient network failures (`src.net.with_retries`).
        use_cache (bool): set False to force a fresh fetch and overwrite the cache
            (e.g. after a statsbombpy upgrade changes the schema).

    Returns:
        The cached or freshly produced object.
    """
    path = CACHE_DIR / f"{kind}_{match_id}.pkl"
    if use_cache and path.exists():
        with open(path, "rb") as cache_file:
            return pickle.load(cache_file)

    _announce_first_download()
    result = with_retries(producer, describe=f"{kind} {match_id}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as cache_file:
        pickle.dump(result, cache_file)
    return result


def load_competitions():
    """Return all competitions available in StatsBomb open data.

    Returns:
        pandas.DataFrame: one row per competition/season.
    """
    return with_retries(_statsbomb().competitions, describe="competitions")


def load_matches(competition_id, season_id):
    """Return match metadata for a given competition and season.

    Args:
        competition_id (int): StatsBomb competition id.
        season_id (int): StatsBomb season id.

    Returns:
        pandas.DataFrame: one row per match.
    """
    return with_retries(
        lambda: _statsbomb().matches(competition_id=competition_id, season_id=season_id),
        describe=f"matches {competition_id}/{season_id}",
    )


def load_events(match_id, use_cache=True):
    """Return granular event data (shots, passes, pressures, etc.) for a match.

    Args:
        match_id (int): StatsBomb match id.
        use_cache (bool): read from / write to the per-match disk cache (default True).

    Returns:
        pandas.DataFrame: one row per event.
    """
    return _disk_cached("events", match_id, lambda: _statsbomb().events(match_id=match_id), use_cache)


def load_lineups(match_id, use_cache=True):
    """Return player lineups for a match.

    Args:
        match_id (int): StatsBomb match id.
        use_cache (bool): read from / write to the per-match disk cache (default True).

    Returns:
        dict[str, pandas.DataFrame]: lineup per team, keyed by team name.
    """
    return _disk_cached("lineups", match_id, lambda: _statsbomb().lineups(match_id=match_id), use_cache)


def load_360_frames(match_id, use_cache=True):
    """Return 360 freeze-frame data (visible player positions per event) for a match.

    Only available for a subset of StatsBomb matches (see `src/config.py` `has_360` flags).

    Args:
        match_id (int): StatsBomb match id.
        use_cache (bool): read from / write to the per-match disk cache (default True).

    Returns:
        pandas.DataFrame: one row per freeze frame.
    """
    return _disk_cached("360", match_id, lambda: _statsbomb().frames(match_id=match_id), use_cache)


def load_skillcorner_tracking(match_id):
    """Return SkillCorner open broadcast tracking data for a match via kloppy.

    Not disk-cached here: kloppy already streams from the SkillCorner open-data repo and
    returns a rich dataset object rather than a plain DataFrame.

    Args:
        match_id (int): SkillCorner open data match id.

    Returns:
        kloppy.domain.TrackingDataset: tracking frames for the match.
    """
    from kloppy import skillcorner  # lazy for the same reason as `_statsbomb`

    return skillcorner.load_open_data(match_id=match_id)
