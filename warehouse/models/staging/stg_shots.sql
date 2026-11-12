-- One row per shot, typed and named for the marts. No business logic here.
select
    match_id,
    competition_id,
    player,
    team,
    minute,
    x,
    y,
    distance_to_goal,
    angle_to_goal,
    shot_body_part,
    is_header,
    is_penalty,
    is_free_kick,
    assist_type,
    cast(is_goal as integer) as goal,
    predicted_xg as xg,
    shot_statsbomb_xg as statsbomb_xg
from {{ source('app_data', 'shots_with_xg') }}
