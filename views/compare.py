"""Compare (TEMPORARY, redesign 1b stage B): the pre-redesign view until stage C replaces it."""

from views import legacy
from views.data import load_pool, load_xg_table

pool = load_pool()
legacy.render_compare_players(pool.per90, load_xg_table(), pool.market_values.reset_index())
