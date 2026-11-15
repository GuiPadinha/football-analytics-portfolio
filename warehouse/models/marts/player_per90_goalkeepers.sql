-- One row per goalkeeper, club and season with at least `min_minutes` on the pitch.
-- save_pct is the share of shots on target he stopped: every one of them ends as a save or a
-- goal, so saves + goals conceded is the denominator. Columns are named one by one, in the
-- pandas table's order (save_pct right after minutes_played), because the app build reads this
-- mart in that table's place (src/warehouse_tables.py).
with keepers as (
    select * from ({{ season_per90(goalkeeper_actions()) }})
    where position_group = 'Goalkeeper'
)

select
    competition_id, season_id, competition,
    player, nickname, team, position_group, minutes_played,
    case when saves + goals_conceded > 0 then saves / (saves + goals_conceded) else 0.0 end
        as save_pct
    {% for action in goalkeeper_actions() %}, {{ action }}{% endfor %}
    {% for action in goalkeeper_actions() %}, {{ action }}_p90{% endfor %}
from keepers
