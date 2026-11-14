{% set rates = [] %}
{% for action in outfield_actions() %}{% do rates.append(action ~ '_p90') %}{% endfor %}
{{ per90_parity('player_per90_outfield', outfield_actions() + ['goals'], rates,
                "position_group <> 'Goalkeeper'") }}
