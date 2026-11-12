-- Parity: the dbt mart must reproduce the pandas-built table the app ships, row for row.
-- Any row returned is a player missing from one side or a number that differs.
with dbt as (
    select player, team, shots, goals, total_xg, xg_diff from {{ ref('player_xg') }}
),

pandas as (
    select player, team, shots, goals, total_xg, xg_diff from {{ source('app_data', 'player_xg_table') }}
)

select
    coalesce(dbt.player, pandas.player) as player,
    coalesce(dbt.team, pandas.team) as team,
    dbt.shots as dbt_shots, pandas.shots as pandas_shots,
    dbt.goals as dbt_goals, pandas.goals as pandas_goals,
    dbt.total_xg as dbt_xg, pandas.total_xg as pandas_xg
from dbt
full outer join pandas
    on dbt.player = pandas.player and dbt.team = pandas.team
where dbt.player is null
   or pandas.player is null
   or dbt.shots <> pandas.shots
   or dbt.goals <> pandas.goals
   or abs(dbt.total_xg - pandas.total_xg) > 1e-9
   or abs(dbt.xg_diff - pandas.xg_diff) > 1e-9
