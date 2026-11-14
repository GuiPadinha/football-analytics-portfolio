-- One row per match event, straight from the landed Parquet (src/landing.py): renamed and typed,
-- no business logic. Only the columns a model downstream uses are named here; the raw files keep
-- every StatsBomb column, so adding one later is a line in this select.
select
    id as event_id,
    match_id,
    competition_id,
    season_id,
    index as event_index,  -- StatsBomb's sequence number within the match: the only safe order
    period,
    minute,
    second,
    type as event_type,
    team,
    player,
    player_id,
    location[1] as x,  -- DuckDB lists are 1-based
    location[2] as y,
    coalesce(under_pressure, false) as under_pressure,  -- StatsBomb writes true or nothing
    shot_outcome,
    shot_type,
    shot_body_part,
    coalesce(shot_first_time, false) as shot_first_time,
    shot_statsbomb_xg,
    shot_key_pass_id,
    coalesce(pass_cross, false) as pass_cross,
    coalesce(pass_through_ball, false) as pass_through_ball,
    coalesce(pass_cut_back, false) as pass_cut_back
from {{ source('raw', 'events') }}
