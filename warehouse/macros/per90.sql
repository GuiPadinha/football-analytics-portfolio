{# The action columns live here once, so the marts and the parity tests cannot drift apart. #}

{% macro outfield_actions() %}
    {{ return(['non_penalty_goals', 'shots', 'key_passes', 'assists', 'progressive_passes',
               'dribbles_completed', 'pressures', 'interceptions', 'tackles', 'clearances',
               'blocks']) }}
{% endmacro %}

{% macro goalkeeper_actions() %}
    {{ return(['saves', 'goals_conceded', 'claims', 'punches', 'sweeper_actions']) }}
{% endmacro %}

{% macro season_per90(actions, extra_counts=[]) %}
-- Season minutes joined to season action totals, then one per-90 rate per action.
with season_actions as (
    select
        competition_id, season_id, team, player
        {% for action in actions + extra_counts %}, sum({{ action }}) as {{ action }}{% endfor %}
    from {{ ref('int_player_match_actions') }}
    group by all
)

select
    seasons.competition_id,
    seasons.season_id,
    competitions.competition,  -- the app's name for the league; null outside its player pool
    seasons.player,
    seasons.nickname,
    seasons.team,
    seasons.position_group,
    seasons.minutes_played
    {% for action in actions + extra_counts %}
    , coalesce(season_actions.{{ action }}, 0) as {{ action }}
    {% endfor %}
    {% for action in actions %}
    , coalesce(season_actions.{{ action }}, 0) / seasons.minutes_played * 90 as {{ action }}_p90
    {% endfor %}
from {{ ref('int_player_seasons') }} as seasons
left join season_actions
    on season_actions.competition_id = seasons.competition_id
    and season_actions.season_id = seasons.season_id
    and season_actions.team = seasons.team and season_actions.player = seasons.player
left join {{ ref('competitions') }} as competitions
    on competitions.competition_id = seasons.competition_id
    and competitions.season_id = seasons.season_id
where seasons.minutes_played >= {{ var('min_minutes') }}
{% endmacro %}

{% macro per90_parity(model, counts, rates, where_pandas) %}
-- Parity with the table the app ships (app_data/player_per90.parquet), for every StatsBomb
-- league that has been landed: same players, same group, same counts; minutes and rates
-- within 1e-9 (sums of floats added in a different order differ in the last bits). Any row
-- returned is a mismatch. A league not landed yet is skipped, not failed: the second test
-- below (assert_every_app_league_is_landed) is the one that says which are missing.
with dbt as (
    select * from {{ ref(model) }} where competition is not null
),

pandas as (
    select * from {{ source('app_data', 'player_per90') }}
    where provider = 'statsbomb' and {{ where_pandas }}
      and competition in (select competition from dbt)
)

select
    coalesce(dbt.competition, pandas.competition) as competition,
    coalesce(dbt.player, pandas.player) as player,
    coalesce(dbt.team, pandas.team) as team
from dbt
full outer join pandas
    on dbt.competition = pandas.competition
    and dbt.player = pandas.player and dbt.team = pandas.team
where dbt.player is null
   or pandas.player is null
   or dbt.position_group <> pandas.position_group
   or dbt.nickname is distinct from pandas.nickname
   or abs(dbt.minutes_played - pandas.minutes_played) > 1e-9
   {% for column in counts %}
   or dbt.{{ column }} <> pandas.{{ column }}
   {% endfor %}
   {% for column in rates %}
   or abs(dbt.{{ column }} - pandas.{{ column }}) > 1e-9
   {% endfor %}
{% endmacro %}
