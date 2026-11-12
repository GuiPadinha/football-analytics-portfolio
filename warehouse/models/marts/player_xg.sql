-- Goals against chances per player (and club): the app's finishing table, plus the
-- non-penalty view scouts use, since a penalty taker's xG is padded by ~0.8 a kick (91 in 2015/16, 74 scored).
with by_player as (
    select
        player,
        team,
        count(*) as shots,
        sum(goal) as goals,
        sum(xg) as total_xg,
        sum(goal) filter (where not is_penalty) as non_penalty_goals,
        coalesce(sum(xg) filter (where not is_penalty), 0) as non_penalty_xg,
        count(*) filter (where is_penalty) as penalties
    from {{ ref('stg_shots') }}
    group by player, team
)

select
    player,
    team,
    shots,
    goals,
    total_xg,
    goals - total_xg as xg_diff,
    total_xg / shots as xg_per_shot,
    penalties,
    coalesce(non_penalty_goals, 0) as non_penalty_goals,
    non_penalty_xg,
    coalesce(non_penalty_goals, 0) - non_penalty_xg as non_penalty_xg_diff
from by_player
