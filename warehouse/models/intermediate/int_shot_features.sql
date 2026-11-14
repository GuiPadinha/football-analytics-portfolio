-- One row per in-game shot with the xG model's features, built from the raw events.
-- The SQL twin of src/features.py `extract_shot_features`; the parity test
-- (tests/assert_shot_features_match_pandas.sql) holds the two together.
with shots as (
    -- Penalty shoot-outs (period 5) are not in-game play: they convert at ~75% and would
    -- distort both the penalty base rate and the score state.
    select * from {{ ref('stg_events') }}
    where event_type = 'Shot' and period <> 5
),

passes as (
    select match_id, event_id, pass_cross, pass_through_ball, pass_cut_back
    from {{ ref('stg_events') }}
    where event_type = 'Pass'
),

with_score as (
    -- Goals before this shot, for the shooter's team and for the match. "Rows between unbounded
    -- preceding and 1 preceding" stops one shot short, so a goal never counts in its own state.
    -- Computed before the location filter below: a goal with no recorded location still
    -- changes the score.
    select
        *,
        coalesce(sum(cast(shot_outcome = 'Goal' as integer)) over (
            partition by match_id, team order by event_index
            rows between unbounded preceding and 1 preceding
        ), 0) as team_goals_before,
        coalesce(sum(cast(shot_outcome = 'Goal' as integer)) over (
            partition by match_id order by event_index
            rows between unbounded preceding and 1 preceding
        ), 0) as match_goals_before
    from shots
)

select
    s.event_id,
    s.match_id,
    s.competition_id,
    s.season_id,
    s.event_index,
    s.player,
    s.team,
    s.minute,
    s.x,
    s.y,
    -- StatsBomb's pitch is 120 x 80; the goal is on x = 120, posts at y = 36 and y = 44.
    sqrt(power(120 - s.x, 2) + power(40 - s.y, 2)) as distance_to_goal,
    -- The angle between the two lines from the ball to the posts: how much goal the shooter
    -- sees. cos = (a · b) / (|a| |b|), clamped to [-1, 1] against rounding.
    degrees(acos(least(1.0, greatest(-1.0,
        ((120 - s.x) * (120 - s.x) + (44 - s.y) * (36 - s.y))
        / (sqrt(power(120 - s.x, 2) + power(44 - s.y, 2))
           * sqrt(power(120 - s.x, 2) + power(36 - s.y, 2)))
    )))) as angle_to_goal,
    s.shot_body_part,
    coalesce(s.shot_body_part = 'Head', false) as is_header,
    s.shot_first_time as is_first_time,
    s.under_pressure,
    coalesce(s.shot_type = 'Penalty', false) as is_penalty,
    coalesce(s.shot_type = 'Free Kick', false) as is_free_kick,
    -- The pass that made the shot, in the order src/features.py checks the flags.
    case
        when p.event_id is null then 'None'
        when p.pass_cross then 'Cross'
        when p.pass_through_ball then 'Through Ball'
        when p.pass_cut_back then 'Cut Back'
        else 'Standard Pass'
    end as assist_type,
    -- Shooter's goals minus the opponent's, before the shot. Own goals are separate events in
    -- StatsBomb and are not counted, the same accepted simplification as in pandas.
    s.team_goals_before - (s.match_goals_before - s.team_goals_before) as game_state_score_diff,
    s.shot_statsbomb_xg,
    coalesce(s.shot_outcome = 'Goal', false) as is_goal
from with_score as s
left join passes as p
    on p.match_id = s.match_id and p.event_id = s.shot_key_pass_id
where s.x is not null  -- a shot with no location cannot be placed on the pitch
