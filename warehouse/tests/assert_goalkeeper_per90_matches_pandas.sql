{% set rates = ['save_pct'] %}
{% for action in goalkeeper_actions() %}{% do rates.append(action ~ '_p90') %}{% endfor %}
{{ per90_parity('player_per90_goalkeepers', goalkeeper_actions(), rates,
                "position_group = 'Goalkeeper'") }}
