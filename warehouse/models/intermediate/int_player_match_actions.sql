-- One row per player and match: raw counts of what he did, outfield and goalkeeper actions
-- side by side. Counts, not rates: they are summed over the season and divided by minutes
-- once, so no single match's small sample distorts the rate.
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
group by all
