"""Wyscout public dataset ingestion (Phase 4e, 2026-10-17): per-90 tables for a 2017/18 pool.

Source: Pappalardo et al., "A public data set of spatio-temporal match events in soccer
competitions", *Scientific Data* 2019, CC BY 4.0, on figshare (collection 4415000). Every match of
the five big men's leagues in 2017/18, as one JSON file per competition inside `events.zip`
(77 MB, ~950 MB unzipped). Downloaded once into `<cache>/wyscout/`, next to the StatsBomb cache.

**Why this is its own module, not another `Dataset` through `similarity.py`:** Wyscout logs the
same football differently (measured 2026-10-17, ML_LEARNING_LOG.md). Pressures and blocks don't
exist, a Wyscout "interception" is about 4x as frequent as StatsBomb's, a "key pass" about 0.3x.
So the tables built here use their own column list (`WY_ACTION_COLUMNS`), and their players must
never share a similarity space with StatsBomb players. The output *shape* matches
`similarity.build_season_per90_tables` (same identity columns, `<action>` totals plus
`<action>_p90` rates), so the app's pool code can stack the two and keep them apart by provider.

Other differences from the StatsBomb build, each a deliberate simplification:
- **Position group** comes from the player's Wyscout `role` (GK/DF/MD/FW), one per player, not
  minutes per position per match: the public set has no per-match positions.
- **Minutes** come from the match sheet: starters from 0, substitutes from their minute, a red
  card ends a player's match, and full time is 90 or the latest substitution if later. StatsBomb's
  lineups include stoppage time, so Wyscout minutes run a few percent lower. That's a level shift
  within one provider, which the per-league normalisation absorbs.
- **Coordinates** (only used for progressive passes) are converted from Wyscout's 0-100,
  landmark-normalised pitch to StatsBomb's 120x80 yards with kloppy's piecewise transform, so
  "10 yards forward" means the same distance in both builds.

Usage (build-time only; the app reads `app_data/`, never this module):
    from src.wyscout import build_wyscout_per90_tables
    outfield, goalkeepers = build_wyscout_per90_tables(config.WYSCOUT_PL_2017_18)
"""

import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from functools import lru_cache

import numpy as np
import pandas as pd

from src.data_loader import CACHE_DIR
from src.net import use_os_trust_store, with_retries, write_atomically

FIGSHARE_URL = "https://ndownloader.figshare.com/files/{}"
# figshare file ids of the four files used (collection 4415000, checked 2026-10-17).
FIGSHARE_FILE_IDS = {
    "events.zip": 14464685,
    "matches.zip": 14464622,
    "players.json": 15073721,
    "teams.json": 15073697,
}
WYSCOUT_CACHE_DIR = CACHE_DIR / "wyscout"

# Wyscout competition id -> the area name its files are called by (`events_England.json`).
AREA_BY_COMPETITION = {364: "England", 795: "Spain", 524: "Italy", 426: "Germany", 412: "France"}

ROLE_TO_POSITION_GROUP = {"GK": "Goalkeeper", "DF": "Defender", "MD": "Midfielder", "FW": "Forward"}

# Event and sub-event ids (the dataset's eventid2name.csv) and tag ids (tags2name.csv).
EVENT_FREE_KICK = 3
EVENT_GOALKEEPER_LEAVING_LINE = 4
EVENT_PASS = 8
EVENT_SAVE_ATTEMPT = 9
SUBEVENT_SHOT = 100
SUBEVENT_FREE_KICK_SHOT = 33
SUBEVENT_PENALTY = 35
SUBEVENT_GROUND_ATTACKING_DUEL = 11
SUBEVENT_GROUND_DEFENDING_DUEL = 12
SUBEVENT_CLEARANCE = 71
TAG_GOAL = 101
TAG_ASSIST = 301
TAG_KEY_PASS = 302
TAG_TAKE_ON_LEFT = 503
TAG_TAKE_ON_RIGHT = 504
TAG_INTERCEPTION = 1401
TAG_SLIDING_TACKLE = 1601
TAG_WON = 703
TAG_ACCURATE = 1801

SHOT_SUBEVENTS = {SUBEVENT_SHOT, SUBEVENT_FREE_KICK_SHOT, SUBEVENT_PENALTY}

# StatsBomb's progressive-pass threshold (`similarity.extract_player_match_actions`), in yards.
PROGRESSIVE_PASS_YARDS = 10
# A league match lasts 90 minutes on the match sheet; substitutions in stoppage time go past it.
REGULATION_MINUTES = 90
# The one season the public set covers for the leagues.
SEASON = "2017/18"

# The outfield stats a Wyscout player is described by: StatsBomb's `ACTION_COLUMNS` minus
# pressures and blocks, which Wyscout doesn't log. Same names, so the app's labels and charts
# carry over, but not the same definitions for every one: key passes and interceptions mean
# different things (see the module docstring), which is why the two providers never mix.
WY_ACTION_COLUMNS = [
    "non_penalty_goals", "shots", "key_passes", "assists", "progressive_passes",
    "dribbles_completed", "interceptions", "tackles", "clearances",
]
WY_DISPLAY_COUNT_COLUMNS = ["goals"]
# Keepers: no claims or punches in Wyscout, so saves, goals conceded and sweeper actions
# ("Goalkeeper leaving line").
WY_GK_ACTION_COLUMNS = ["saves", "goals_conceded", "sweeper_actions"]
WY_PER90_FEATURE_COLUMNS = [f"{col}_p90" for col in WY_ACTION_COLUMNS]
WY_GK_PER90_FEATURE_COLUMNS = [f"{col}_p90" for col in WY_GK_ACTION_COLUMNS]

IDENTITY_COLUMNS = ["player_id", "player", "nickname", "birth_date", "team", "position_group",
                    "minutes_played"]
WY_PER90_TABLE_COLUMNS = (
    IDENTITY_COLUMNS + WY_ACTION_COLUMNS + WY_DISPLAY_COUNT_COLUMNS + WY_PER90_FEATURE_COLUMNS
)
WY_GK_TABLE_COLUMNS = (
    IDENTITY_COLUMNS + ["save_pct"] + WY_GK_ACTION_COLUMNS + WY_GK_PER90_FEATURE_COLUMNS
)

_ESCAPED_CODEPOINT = re.compile(r"\\u([0-9a-fA-F]{4})")


def unescape_name(text):
    """Undo the dataset's double escaping of non-ASCII names, and trim stray spaces.

    `players.json` stores "Kanté" as the literal characters `Kant\\u00e9` (the escape survives JSON
    decoding), and some names carry a trailing space ("Mohamed "). Left alone, those names would
    neither display right nor match Transfermarkt.

    Args:
        text (str | None): a name field as decoded from the JSON.

    Returns:
        str | None: the readable name, or None for a missing/empty one.
    """
    if not text:
        return None
    readable = _ESCAPED_CODEPOINT.sub(lambda match: chr(int(match.group(1), 16)), text).strip()
    return readable or None


_LEADING_INITIAL = re.compile(r"^([^\W\d_])\.\s+(.+)$")


def popular_name(first_name, short_name):
    """The name a fan knows, rebuilt from Wyscout's short name and the player's first name.

    Wyscout's `shortName` is either the popular name already ("Neymar", "Cristiano Ronaldo") or
    an initial plus surname ("L. Messi"). The full name is often a registered legal name
    ("Lionel Andrés Messi Cuccittini"), so the initial is spelled out with the first given name
    instead: "Lionel Messi", "Riyad Mahrez", "N'Golo Kanté". The initial can belong to a middle
    name ("D. Faraoni" is Marco Davide Faraoni, known as Davide), so the first given name with
    that initial is used. With none (Bamidele "Dele" Alli), the short name is kept as it is.

    Args:
        first_name (str | None): unescaped `firstName`.
        short_name (str | None): unescaped `shortName`.

    Returns:
        str | None: the popular name, or None when there is no short name.
    """
    if not short_name:
        return None
    match = _LEADING_INITIAL.match(short_name)
    if not match or not first_name:
        return short_name
    initial, surname = match.group(1).casefold(), match.group(2)
    given = next((name for name in first_name.split() if name[0].casefold() == initial), None)
    return f"{given} {surname}" if given else short_name


def _cached_file(name):
    """Path to one of the dataset's files, downloading it into the cache on first use."""
    path = WYSCOUT_CACHE_DIR / name
    if not path.exists():
        use_os_trust_store()
        WYSCOUT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = FIGSHARE_URL.format(FIGSHARE_FILE_IDS[name])
        print(f"Downloading Wyscout {name} into {WYSCOUT_CACHE_DIR}")

        def fetch():
            with urllib.request.urlopen(url, timeout=300) as response:
                return response.read()

        write_atomically(path, with_retries(fetch, describe=f"wyscout {name}"))
    return path


def _read_zipped_json(zip_name, member):
    """Parse one JSON member of a cached zip without extracting it to disk."""
    with zipfile.ZipFile(_cached_file(zip_name)) as archive:
        return json.loads(archive.read(member).decode("utf-8"))


def load_competition(competition_id):
    """One competition's match sheets and events, as the dataset's raw dicts.

    Args:
        competition_id (int): a Wyscout competition id in `AREA_BY_COMPETITION`.

    Returns:
        tuple[list[dict], list[dict]]: (matches, events).
    """
    area = AREA_BY_COMPETITION[competition_id]
    matches = _read_zipped_json("matches.zip", f"matches_{area}.json")
    events = _read_zipped_json("events.zip", f"events_{area}.json")
    return matches, events


def load_players():
    """Wyscout's player register: id -> name, popular name, birth date and position group.

    Returns:
        dict[int, dict]: per player id, `player` (first + last name), `nickname` (the name he's
            known by, see `popular_name`), `birth_date` (a Timestamp, the strongest identity
            signal for market-value matching) and `position_group`.
    """
    players = json.loads(_cached_file("players.json").read_text(encoding="utf-8"))
    register = {}
    for row in players:
        first, last = unescape_name(row.get("firstName")), unescape_name(row.get("lastName"))
        short = unescape_name(row.get("shortName"))
        register[row["wyId"]] = {
            "player": " ".join(part for part in (first, last) if part) or short,
            "nickname": popular_name(first, short),
            "birth_date": pd.to_datetime(row.get("birthDate"), errors="coerce"),
            "position_group": ROLE_TO_POSITION_GROUP.get(row["role"]["code2"]),
        }
    return register


def load_team_names():
    """Wyscout team id -> club name (e.g. 1613 -> "Newcastle United")."""
    teams = json.loads(_cached_file("teams.json").read_text(encoding="utf-8"))
    return {row["wyId"]: unescape_name(row["name"]) for row in teams}


@lru_cache(maxsize=1)
def _yard_lookup():
    """Wyscout's integer 0-100 coordinates -> StatsBomb yards, one table per axis.

    kloppy's transform between the two pitches is piecewise linear and acts on each axis
    separately, and Wyscout only ever records whole numbers, so a 101-entry table per axis is
    exact and vectorises what would otherwise be a per-point kloppy call on millions of passes.
    Imported lazily: kloppy is a build-time dependency, not an app one.

    Returns:
        tuple[numpy.ndarray, numpy.ndarray]: (x yards, y yards), indexed by the Wyscout value.
    """
    from kloppy.domain import Dimension, Point
    from kloppy.domain.models.pitch import ImperialPitchDimensions, WyscoutPitchDimensions

    wyscout = WyscoutPitchDimensions()
    statsbomb = ImperialPitchDimensions(
        x_dim=Dimension(0, 120), y_dim=Dimension(0, 80), standardized=True
    )
    points = [statsbomb.from_metric_base(wyscout.to_metric_base(Point(v, v))) for v in range(101)]
    return np.array([p.x for p in points]), np.array([p.y for p in points])


def to_statsbomb_x(wyscout_x):
    """Convert Wyscout x values (0-100, clipped) to StatsBomb yards (0-120)."""
    x_yards, _ = _yard_lookup()
    return x_yards[np.clip(np.asarray(wyscout_x, dtype=int), 0, 100)]


def _minute(value):
    """A match-sheet minute field ("85", "0", "null", 85) as an int; 0 when absent."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def compute_match_minutes(match):
    """Minutes played by each player in one match, from its match sheet.

    Args:
        match (dict): one entry of the dataset's `matches_<area>.json`.

    Returns:
        list[dict]: one row per player who played, with `player_id`, `team_id` and
            `minutes_played`.
    """
    teams = match["teamsData"].values()
    # The dataset sometimes stores an empty substitution list as the string "null".
    substitutions = {
        team["teamId"]: (team["formation"]["substitutions"]
                         if isinstance(team["formation"]["substitutions"], list) else [])
        for team in teams
    }
    full_time = max(
        [REGULATION_MINUTES] + [sub["minute"] for subs in substitutions.values() for sub in subs]
    )

    rows = []
    for team in teams:
        formation = team["formation"]
        on = {player["playerId"]: 0 for player in formation["lineup"]}
        off = {}
        for sub in substitutions[team["teamId"]]:
            on[sub["playerIn"]] = sub["minute"]
            off[sub["playerOut"]] = sub["minute"]
        # `redCards` holds the minute of the sending-off ("0" when none).
        for player in formation["lineup"] + (formation.get("bench") or []):
            red = _minute(player.get("redCards"))
            if red and player["playerId"] in on:
                off[player["playerId"]] = min(off.get(player["playerId"], full_time), red)
        for player_id, start in on.items():
            minutes = max(off.get(player_id, full_time) - start, 0)
            if minutes > 0:
                rows.append({"player_id": player_id, "team_id": team["teamId"],
                             "minutes_played": minutes})
    return rows


def extract_match_actions(events):
    """Count each player's outfield and goalkeeper actions in a list of Wyscout events.

    One pass over the events fills both column sets; which ones a player keeps is decided later
    by his position group, as in the StatsBomb build. The definitions (first probed 2026-10-17
    against StatsBomb's PL 2015/16 rates, ML_LEARNING_LOG.md):
    - goals / non-penalty goals: a shot, free-kick shot or penalty tagged Goal.
    - shots: shots, free-kick shots and penalties, as StatsBomb's `Shot` includes all three.
    - key passes / assists: the `keyPass` / `assist` tags on a pass or set-piece pass.
    - progressive passes: an accurate pass or set-piece pass ending 10+ yards (StatsBomb units)
      nearer the opponent's goal. Wyscout coordinates face the acting team's attack.
    - dribbles completed: a won ground attacking duel with a take-on tag.
    - tackles: a ground defending duel that was won or was a sliding tackle.
    - interceptions: any event tagged interception (Wyscout's broad definition).
    - clearances: the Clearance sub-event.
    - saves / goals conceded: a keeper's save attempt tagged accurate / Goal.
    - sweeper actions: "Goalkeeper leaving line".

    Args:
        events (list[dict]): raw Wyscout events (any number of matches).

    Returns:
        pandas.DataFrame: one row per (player_id, team_id) with a count column for every entry
            of `WY_ACTION_COLUMNS`, `WY_DISPLAY_COUNT_COLUMNS` and `WY_GK_ACTION_COLUMNS`.
    """
    counts = defaultdict(lambda: defaultdict(int))
    pass_starts, pass_ends, pass_keys = [], [], []
    for event in events:
        key = (event["playerId"], event["teamId"])
        tags = {tag["id"] for tag in event["tags"]}
        event_id, subevent_id = event["eventId"], event["subEventId"]
        row = counts[key]

        if subevent_id in SHOT_SUBEVENTS:
            row["shots"] += 1
            if TAG_GOAL in tags:
                row["goals"] += 1
                if subevent_id != SUBEVENT_PENALTY:
                    row["non_penalty_goals"] += 1
        elif event_id in (EVENT_PASS, EVENT_FREE_KICK):
            row["key_passes"] += TAG_KEY_PASS in tags
            row["assists"] += TAG_ASSIST in tags
            if TAG_ACCURATE in tags and len(event["positions"]) == 2:
                pass_starts.append(event["positions"][0]["x"])
                pass_ends.append(event["positions"][1]["x"])
                pass_keys.append(key)
        elif subevent_id == SUBEVENT_GROUND_ATTACKING_DUEL:
            if TAG_WON in tags and tags & {TAG_TAKE_ON_LEFT, TAG_TAKE_ON_RIGHT}:
                row["dribbles_completed"] += 1
        elif subevent_id == SUBEVENT_GROUND_DEFENDING_DUEL:
            if tags & {TAG_WON, TAG_SLIDING_TACKLE}:
                row["tackles"] += 1
        elif subevent_id == SUBEVENT_CLEARANCE:
            row["clearances"] += 1
        elif event_id == EVENT_SAVE_ATTEMPT:
            if TAG_GOAL in tags:
                row["goals_conceded"] += 1
            elif TAG_ACCURATE in tags:
                row["saves"] += 1
        elif event_id == EVENT_GOALKEEPER_LEAVING_LINE:
            row["sweeper_actions"] += 1
        # Interception is a tag, not an event type: it rides on passes, duels and touches alike.
        row["interceptions"] += TAG_INTERCEPTION in tags

    if pass_keys:
        gained = to_statsbomb_x(pass_ends) - to_statsbomb_x(pass_starts)
        for key, yards in zip(pass_keys, gained):
            if yards >= PROGRESSIVE_PASS_YARDS:
                counts[key]["progressive_passes"] += 1

    all_columns = WY_ACTION_COLUMNS + WY_DISPLAY_COUNT_COLUMNS + WY_GK_ACTION_COLUMNS
    rows = [
        {"player_id": player_id, "team_id": team_id, **{col: row[col] for col in all_columns}}
        for (player_id, team_id), row in counts.items()
    ]
    return pd.DataFrame(rows, columns=["player_id", "team_id"] + all_columns)


def per90_tables(minutes, actions, players, team_names, min_minutes=900, season_label=SEASON):
    """Season minutes + action counts -> (outfield, goalkeepers) per-90 tables. Pure.

    Args:
        minutes (pandas.DataFrame): `compute_match_minutes` rows for the season.
        actions (pandas.DataFrame): `extract_match_actions` output for the season.
        players (dict[int, dict]): `load_players` register.
        team_names (dict[int, str]): `load_team_names` mapping.
        min_minutes (float): minutes floor, as in `similarity.build_player_per90_features`.
            Applied per (player, team), so a January transfer is two rows, as in StatsBomb.
        season_label (str): appended to `player`, the row key ("Harry Kane · 2017/18").

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: exactly `WY_PER90_TABLE_COLUMNS` and
            `WY_GK_TABLE_COLUMNS`.
    """
    season = minutes.groupby(["player_id", "team_id"], as_index=False)["minutes_played"].sum()
    count_columns = WY_ACTION_COLUMNS + WY_DISPLAY_COUNT_COLUMNS + WY_GK_ACTION_COLUMNS
    season_actions = actions.groupby(["player_id", "team_id"], as_index=False)[count_columns].sum()
    table = season.merge(season_actions, on=["player_id", "team_id"], how="left")
    table[count_columns] = table[count_columns].fillna(0)
    table = table[table["minutes_played"] >= min_minutes].copy()

    register = pd.DataFrame.from_dict(players, orient="index")
    table = table.join(register, on="player_id")
    table["team"] = table["team_id"].map(team_names)
    table = table[table["position_group"].notna()]
    # The app keys a row by (player, team), and 329 of these pairs already exist in its StatsBomb
    # 2015/16 rows (Harry Kane at Tottenham is in both seasons), where they would silently pick up
    # the other season's xG and market value. So `player` carries the season; pages show
    # `nickname`, which is filled with the full name when Wyscout has no short name.
    table["nickname"] = table["nickname"].fillna(table["player"])
    table["player"] = table["player"] + f" · {season_label}"

    outfield = table[table["position_group"] != "Goalkeeper"].copy()
    for col in WY_ACTION_COLUMNS:
        outfield[f"{col}_p90"] = outfield[col] / outfield["minutes_played"] * 90

    keepers = table[table["position_group"] == "Goalkeeper"].copy()
    on_target = keepers["saves"] + keepers["goals_conceded"]
    keepers["save_pct"] = (keepers["saves"] / on_target).where(on_target > 0, 0.0)
    for col in WY_GK_ACTION_COLUMNS:
        keepers[f"{col}_p90"] = keepers[col] / keepers["minutes_played"] * 90

    return (
        outfield[WY_PER90_TABLE_COLUMNS].reset_index(drop=True),
        keepers[WY_GK_TABLE_COLUMNS].reset_index(drop=True),
    )


def build_wyscout_per90_tables(dataset, min_minutes=900):
    """Outfield and goalkeeper per-90 tables for one Wyscout competition/season.

    The Wyscout counterpart of `similarity.build_season_per90_tables`.

    Args:
        dataset (config.Dataset): one of `config.WYSCOUT_SETS`.
        min_minutes (float): minutes floor applied to both tables.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: see `per90_tables`.
    """
    matches, events = load_competition(dataset.comp_id)
    minutes = pd.DataFrame([row for match in matches for row in compute_match_minutes(match)])
    actions = extract_match_actions(events)
    return per90_tables(minutes, actions, load_players(), load_team_names(), min_minutes)
