-- Team names as each source writes them, mapped to the match sheet's names.
-- StatsBomb sometimes names a club differently inside a match than on the season's match list
-- (Ligue 1 2015/16: "Marseille" for "Olympique de Marseille"), which split a player's season in
-- two when grouping by team. A match has two teams, so one unknown name can only be the sheet
-- name nobody else took. Two unknown names would be a guess: `team` stays null and the
-- not_null test fails the build (src/similarity.py `canonical_team_names` raises instead).
with names as (
    select distinct match_id, 'lineups' as source, team as source_name
    from {{ ref('stg_lineup_stints') }}
    union all
    select distinct match_id, 'events' as source, team as source_name
    from {{ ref('stg_events') }}
    where team is not null
),

checked as (
    select
        names.match_id,
        names.source,
        names.source_name,
        matches.home_team,
        matches.away_team,
        names.source_name in (matches.home_team, matches.away_team) as on_sheet,
        count(*) filter (where names.source_name not in (matches.home_team, matches.away_team))
            over (partition by names.match_id, names.source) as unknown_names,
        bool_or(names.source_name = matches.home_team)
            over (partition by names.match_id, names.source) as home_taken,
        bool_or(names.source_name = matches.away_team)
            over (partition by names.match_id, names.source) as away_taken
    from names
    inner join {{ ref('stg_matches') }} as matches on matches.match_id = names.match_id
)

select
    match_id,
    source,
    source_name,
    case
        when on_sheet then source_name
        when unknown_names = 1 and home_taken and not away_taken then away_team
        when unknown_names = 1 and away_taken and not home_taken then home_team
    end as team
from checked
