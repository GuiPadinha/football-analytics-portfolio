"""Player Evaluation Framework: the Streamlit app's entry point and top navigation.

The app reads precomputed tables from `app_data/` and never downloads or trains anything, so a
hosted demo responds to a click. This file only sets the page frame, loads the stylesheet and
routes; each page is a script under `views/`, and what a page says about a player is decided in
`src/profile.py` and `src/narrative.py` (docs/PRODUCT_SPEC.md has the page-to-function map).

Run locally: streamlit run app.py
"""

import streamlit as st

from views.components import stylesheet_html

st.set_page_config(page_title="Player Evaluation", page_icon="⚽", layout="wide")
st.html(stylesheet_html())

st.navigation(
    [
        st.Page("views/home.py", title="Home", default=True),
        st.Page("views/players.py", title="Players"),
        st.Page("views/compare.py", title="Compare"),
        st.Page("views/leaderboard.py", title="Leaderboard"),
        st.Page("views/how_it_works.py", title="How it works"),
    ],
    position="top",
).run()
