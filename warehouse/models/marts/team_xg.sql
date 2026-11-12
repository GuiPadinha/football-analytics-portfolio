-- Goals against chances per club. Not in the app yet: the first table that exists only here.
select
    team,
    count(distinct player) as shooters,
    sum(shots) as shots,
    sum(goals) as goals,
    sum(total_xg) as total_xg,
    sum(goals) - sum(total_xg) as xg_diff,
    sum(non_penalty_goals) as non_penalty_goals,
    sum(non_penalty_xg) as non_penalty_xg
from {{ ref('player_xg') }}
group by team
