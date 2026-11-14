"""Player Evaluation Framework: the Streamlit app's entry point and top navigation.

The app reads precomputed tables from `app_data/` and never downloads or trains anything, so a
hosted demo responds to a click. This file only sets the page frame, loads the stylesheet and
routes; each page is a script under `views/`, and what a page says about a player is decided in
`src/profile.py` and `src/narrative.py` (docs/PRODUCT_SPEC.md has the page-to-function map).

Run locally: streamlit run app.py
"""

from pathlib import Path

import streamlit as st

from src.freshness import code_fingerprint, purge_project_modules


@st.cache_resource
def _last_seen_code() -> dict:
    """One dict per server process, shared by every session: the code fingerprint last seen."""
    return {"fingerprint": None}


# A push changes files under a running process; without this, pages can import stale shared
# modules until a manual reboot (src/freshness.py has the why). Runs before any project import.
_seen = _last_seen_code()
_now = code_fingerprint(Path(__file__).parent)
if _seen["fingerprint"] is not None and _seen["fingerprint"] != _now:
    purge_project_modules()
    st.cache_data.clear()
_seen["fingerprint"] = _now

from views.components import stylesheet_html  # noqa: E402 (must follow the freshness check)

st.set_page_config(page_title="Player Evaluation", page_icon="⚽", layout="wide")
st.html(stylesheet_html())

st.navigation(
    [
        st.Page("views/home.py", title="Home", default=True),
        st.Page("views/players.py", title="Players"),
        st.Page("views/compare.py", title="Compare"),
        st.Page("views/leaderboard.py", title="Leaderboard"),
        st.Page("views/build.py", title="Build a player"),
        st.Page("views/how_it_works.py", title="How it works"),
    ],
    position="top",
).run()
