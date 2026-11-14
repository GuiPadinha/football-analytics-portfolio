-- Parity: the shot features built in SQL from the raw events must equal the ones pandas built
-- for the table the app ships (Premier League 2015/16), shot for shot and column for column.
-- Any row returned is a difference. Two checks, because shots_with_xg carries no event id:
--   1. `except all` on the exact columns. It keeps duplicates, so two identical shots on one
--      side and one on the other fail.
--   2. distance and angle depend only on (x, y), so they are compared per location with a
--      tolerance: numpy and DuckDB can differ in the last bit of a float, and rounding both
--      sides does not fix that (9,908 shots, one fell on a rounding boundary).
{% set exact_columns %}
    match_id, player, team, minute, x, y,
    shot_body_part, is_header, is_first_time, under_pressure, is_penalty, is_free_kick,
    assist_type, game_state_score_diff, shot_statsbomb_xg, is_goal
{% endset %}
with dbt as (
    select * from {{ ref('int_shot_features') }} where competition_id = 2
),

pandas as (
    select * from {{ source('app_data', 'shots_with_xg') }}
),

dbt_exact as (select {{ exact_columns }} from dbt),

pandas_exact as (select {{ exact_columns }} from pandas),

geometry as (
    select distinct
        dbt.x, dbt.y,
        dbt.distance_to_goal as dbt_distance, pandas.distance_to_goal as pandas_distance,
        dbt.angle_to_goal as dbt_angle, pandas.angle_to_goal as pandas_angle
    from dbt
    inner join pandas on dbt.x = pandas.x and dbt.y = pandas.y
)

(select 'only in dbt' as problem, match_id, player, minute, x, y
 from (select * from dbt_exact except all select * from pandas_exact))
union all
(select 'only in pandas' as problem, match_id, player, minute, x, y
 from (select * from pandas_exact except all select * from dbt_exact))
union all
(select 'distance or angle differs' as problem, null, null, null, x, y
 from geometry
 where abs(dbt_distance - pandas_distance) > 1e-9 or abs(dbt_angle - pandas_angle) > 1e-9)
