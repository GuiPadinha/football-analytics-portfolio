-- One row per goalkeeper, club and season with at least `min_minutes` on the pitch.
-- save_pct is the share of shots on target he stopped: every one of them ends as a save or a
-- goal, so saves + goals conceded is the denominator.
select
    *,
    case when saves + goals_conceded > 0 then saves / (saves + goals_conceded) else 0.0 end
        as save_pct
from ({{ season_per90(goalkeeper_actions()) }})
where position_group = 'Goalkeeper'
