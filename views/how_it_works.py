"""How it works (TEMPORARY, redesign 1b stage B): the pre-redesign About view until stage D."""

from views import legacy
from views.data import load_metrics, load_pool

legacy.render_about_and_roadmap(load_pool().per90, load_metrics())
