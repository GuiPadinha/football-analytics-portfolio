-- One row per player and match: raw counts of what he did, outfield and goalkeeper actions
-- side by side. Counts, not rates: they are summed over the season and divided by minutes
-- once, so no single match's small sample distorts the rate.
--
-- Incremental, by match. This is the model that reads every event (millions of rows), and a
-- landed match never changes: its events are final once the match is played. So the first run
-- (or `--full-refresh`) builds the whole table, and every later run only aggregates the matches
-- that are not in it yet, then appends them.
--   * is_incremental() is true only when the table already exists in the target database, the
--     run is not a full refresh, and the model is materialized incrementally. In the default
--     in-memory target the table never exists at the start of a run, so it is always a full
--     build there; `python -m tools.warehouse --persist` keeps a DuckDB file between runs.
--   * The unit of "new" is the match, not a timestamp: StatsBomb's files carry no load date, and
--     a whole match is the smallest piece that is complete. A partial match cannot be appended.
--   * What this does not catch: a match re-landed with corrected events (`src.landing --force`)
--     keeps its old rows. That is the cost of append; rebuild with `--full-refresh` after one.
--   * on_schema_change = 'fail': a new action column makes the next incremental run stop instead
--     of silently leaving the column null for the old matches. Rebuild with `--full-refresh`.
{{ config(
    materialized = 'incremental',
    incremental_strategy = 'append',
    on_schema_change = 'fail'
) }}

select
    events.match_id,
    events.competition_id,
    events.season_id,
    names.team,
    events.player,

    -- Outfield. Penalties convert at ~75%, so non-penalty goals is the modelling column and
    -- `goals` (penalties included) is for display only.
    count(*) filter (where event_type = 'Shot' and shot_outcome = 'Goal'
                     and shot_type is distinct from 'Penalty') as non_penalty_goals,
    count(*) filter (where event_type = 'Shot' and shot_outcome = 'Goal') as goals,
    count(*) filter (where event_type = 'Shot') as shots,
    -- StatsBomb flags a pass as a shot assist only when the shot did not score; a pass that
    -- set up a goal is a goal assist instead. The two never overlap.
    count(*) filter (where event_type = 'Pass' and pass_shot_assist) as key_passes,
    count(*) filter (where event_type = 'Pass' and pass_goal_assist) as assists,
    -- Progressive: a completed pass (no outcome recorded) that gains 10+ yards towards goal.
    -- Coordinates always attack towards x = 120, so the x difference is enough.
    count(*) filter (where event_type = 'Pass' and pass_outcome is null
                     and pass_end_x - x >= 10) as progressive_passes,
    count(*) filter (where event_type = 'Dribble' and dribble_outcome = 'Complete')
        as dribbles_completed,
    count(*) filter (where event_type = 'Pressure') as pressures,
    count(*) filter (where event_type = 'Interception') as interceptions,
    count(*) filter (where event_type = 'Duel' and duel_type = 'Tackle') as tackles,
    count(*) filter (where event_type = 'Clearance') as clearances,
    count(*) filter (where event_type = 'Block') as blocks,

    -- Goalkeeper. One 'Goal Keeper' event per shot; these types are the shots on target.
    count(*) filter (where event_type = 'Goal Keeper' and goalkeeper_type in (
        'Shot Saved', 'Shot Saved to Post', 'Penalty Saved', 'Penalty Saved to Post')) as saves,
    count(*) filter (where event_type = 'Goal Keeper' and goalkeeper_type in (
        'Goal Conceded', 'Penalty Conceded')) as goals_conceded,
    count(*) filter (where event_type = 'Goal Keeper' and goalkeeper_type = 'Collected') as claims,
    count(*) filter (where event_type = 'Goal Keeper' and goalkeeper_type = 'Punch') as punches,
    count(*) filter (where event_type = 'Goal Keeper' and goalkeeper_type = 'Keeper Sweeper')
        as sweeper_actions
from {{ ref('stg_events') }} as events
inner join {{ ref('int_team_names') }} as names
    on names.match_id = events.match_id and names.source = 'events'
    and names.source_name = events.team
where events.player is not null
{% if is_incremental() %}
    -- {{ this }} is the table as it stands from the previous run: skip every match already in it.
    and events.match_id not in (select distinct match_id from {{ this }})
{% endif %}
group by all
