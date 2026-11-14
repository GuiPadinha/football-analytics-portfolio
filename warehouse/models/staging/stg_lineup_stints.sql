-- One row per stint: a player's spell in one position in one match. The clocks are 'MM:SS'
-- strings on a match clock that does not reset at half-time ('95:12' is second-half stoppage
-- time), so minutes + seconds / 60 is the whole conversion. A stint with no end ran to the
-- final whistle; the model downstream closes it.
select
    match_id,
    competition_id,
    season_id,
    team,
    player_id,
    player_name as player,
    player_nickname as nickname,
    stint_index,
    position,
    cast(split_part(from_clock, ':', 1) as integer)
        + cast(split_part(from_clock, ':', 2) as integer) / 60.0 as from_minute,
    cast(split_part(to_clock, ':', 1) as integer)
        + cast(split_part(to_clock, ':', 2) as integer) / 60.0 as to_minute
from {{ source('raw', 'lineups') }}
