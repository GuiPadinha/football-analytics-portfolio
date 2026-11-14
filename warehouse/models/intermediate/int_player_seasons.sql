-- One row per player, club and season: total minutes, position group and position.
-- The group is the one with the most season MINUTES, not the most matches. A winger whose
-- minutes are split across Right Wing, Left Wing and Center Forward would lose a per-match
-- vote to a handful of games at Right Back; summing by group first reunites his attacking
-- minutes (src/similarity.py `resolve_season_positions`, which reclassified 10 hybrids).
with matches as (
    select minutes.*, groups.position_group
    from {{ ref('int_player_match_minutes') }} as minutes
    left join {{ ref('position_groups') }} as groups on groups.position = minutes.position
),

group_minutes as (
    select
        competition_id, season_id, team, player, position_group,
        sum(minutes_played) as minutes
    from matches
    where position_group is not null
    group by competition_id, season_id, team, player, position_group
    -- `qualify` filters on a window function, as `having` does on an aggregate: keep the
    -- group with the most minutes. A tie goes to the first by name.
    qualify row_number() over (
        partition by competition_id, season_id, team, player
        order by minutes desc, position_group
    ) = 1
),

position_minutes as (
    select
        competition_id, season_id, team, player, position_group, position,
        sum(minutes_played) as minutes
    from matches
    where position_group is not null
    group by competition_id, season_id, team, player, position_group, position
    qualify row_number() over (
        partition by competition_id, season_id, team, player, position_group
        order by minutes desc, position
    ) = 1
),

nicknames as (
    -- The nickname he carries in most matches (StatsBomb's popular name, e.g. "Koke").
    select
        competition_id, season_id, team, player, nickname,
        count(*) as matches_with_it
    from matches
    where nickname is not null
    group by competition_id, season_id, team, player, nickname
    qualify row_number() over (
        partition by competition_id, season_id, team, player
        order by matches_with_it desc, nickname
    ) = 1
),

totals as (
    -- Every minute counts here, in a mapped position or not: the minimum-minutes filter
    -- downstream measures time on the pitch, not time in the winning group.
    select competition_id, season_id, team, player, sum(minutes_played) as minutes_played
    from matches
    group by all
)

select
    totals.competition_id,
    totals.season_id,
    totals.player,
    nicknames.nickname,
    totals.team,
    group_minutes.position_group,
    position_minutes.position,
    totals.minutes_played
from totals
inner join group_minutes  -- inner: a player with no mapped position has no group and is dropped
    on group_minutes.competition_id = totals.competition_id
    and group_minutes.season_id = totals.season_id
    and group_minutes.team = totals.team and group_minutes.player = totals.player
inner join position_minutes
    on position_minutes.competition_id = totals.competition_id
    and position_minutes.season_id = totals.season_id
    and position_minutes.team = totals.team and position_minutes.player = totals.player
    and position_minutes.position_group = group_minutes.position_group
left join nicknames
    on nicknames.competition_id = totals.competition_id
    and nicknames.season_id = totals.season_id
    and nicknames.team = totals.team and nicknames.player = totals.player
