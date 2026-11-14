-- One row per match: the season's match sheet, whose team names are the canonical ones.
select
    match_id,
    competition_id,
    season_id,
    cast(match_date as date) as match_date,
    match_week,
    home_team,
    away_team,
    home_score,
    away_score
from {{ source('raw', 'matches') }}
