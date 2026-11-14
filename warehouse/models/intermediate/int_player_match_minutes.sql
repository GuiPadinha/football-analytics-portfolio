-- One row per player and match: minutes on the pitch and the position played longest.
-- Minutes come from the lineups' stints, not from substitution events: the stints also record
-- position changes during the match.
with match_ends as (
    -- The last minute any event was logged: where a stint with no end time is closed.
    select match_id, max(minute) as final_minute
    from {{ ref('stg_events') }}
    group by match_id
),

by_position as (
    select
        stints.match_id,
        stints.competition_id,
        stints.season_id,
        names.team,
        stints.player,
        stints.position,
        any_value(stints.nickname) as nickname,
        min(stints.stint_index) as first_stint,
        sum(greatest(coalesce(stints.to_minute, match_ends.final_minute) - stints.from_minute, 0))
            as minutes
    from {{ ref('stg_lineup_stints') }} as stints
    inner join match_ends on match_ends.match_id = stints.match_id
    inner join {{ ref('int_team_names') }} as names
        on names.match_id = stints.match_id and names.source = 'lineups'
        and names.source_name = stints.team
    group by all
),

ranked as (
    select
        *,
        sum(minutes) over (partition by match_id, team, player) as minutes_played,
        -- Most minutes wins; on a tie, the position he took up first.
        row_number() over (
            partition by match_id, team, player order by minutes desc, first_stint
        ) as position_rank
    from by_position
)

select match_id, competition_id, season_id, team, player, nickname, position, minutes_played
from ranked
where position_rank = 1
