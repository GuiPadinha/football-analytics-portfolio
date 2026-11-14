-- Coverage: the parity tests only compare leagues that were landed, so on their own they would
-- pass with one league. This one returns every StatsBomb league of the app that the outfield
-- mart does not have. A warning, not an error: landing all nine takes minutes and 1 GB, and
-- a fresh machine may have landed only one.
{{ config(severity='warn') }}
select competitions.competition
from {{ ref('competitions') }} as competitions
where competitions.competition not in (
    select competition from {{ ref('player_per90_outfield') }} where competition is not null
)
