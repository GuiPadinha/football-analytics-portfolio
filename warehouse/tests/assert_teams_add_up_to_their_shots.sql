-- Reconciliation: club totals must add back to the shots they came from, so no shot is dropped
-- or double-counted between staging and the marts.
with from_teams as (
    select sum(shots) as shots, sum(goals) as goals, sum(total_xg) as xg from {{ ref('team_xg') }}
),

from_shots as (
    select count(*) as shots, sum(goal) as goals, sum(xg) as xg from {{ ref('stg_shots') }}
)

select *
from from_teams, from_shots
where from_teams.shots <> from_shots.shots
   or from_teams.goals <> from_shots.goals
   or abs(from_teams.xg - from_shots.xg) > 1e-6
