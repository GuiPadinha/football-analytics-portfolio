"""How it works: the method, the accuracy numbers and the limits, for whoever wants to check.

The player pages state conclusions; this page is where the jargon lives (league adjustment,
distance, silhouette, ROC-AUC) with what each number means. Figures come from `metrics.json` or
are computed from the app tables here, never typed in.
"""

import pandas as pd
import streamlit as st

from src.narrative import CHEAPER_RATIO, RARE_SEASON, STANDOUT_PERCENTILE, UNUSUAL_SEASON
from src.presentation import feature_columns_for
from src.similarity import compute_silhouette_scores
from views import components as ui
from views.data import load_metrics, load_pool

REPO_URL = "https://github.com/GuiPadinha/football-analytics-portfolio/blob/main/docs"
OUTFIELD_AND_KEEPERS = ["Defender", "Midfielder", "Forward", "Goalkeeper"]

metrics = load_metrics()
pool = load_pool()
per90 = pool.per90
xg, ladder = metrics["xg"], metrics["xg"]["baseline_ladder_test_roc_auc"]
tests = pd.DataFrame(metrics["xg_generalisation"].values()).sort_values("roc_auc", ascending=False)
n_test_shots = int(tests["n_shots"].sum())
n_womens_tests = int((tests["gender"] == "female").sum())
outfield_passes = per90[per90["position_group"] != "Goalkeeper"].groupby("gender")["progressive_passes_p90"].median()


@st.cache_data
def silhouettes():
    """Silhouette at K=2 and K=4 for each position group of the app's own pool, in the same
    league-normalised space the lookalikes and styles use."""
    rows = []
    for group in OUTFIELD_AND_KEEPERS:
        part = per90[per90["position_group"] == group]
        scores = compute_silhouette_scores(part[feature_columns_for(group)[2]], k_range=range(2, 5))
        rows.append({"Position": group, "Players": len(part), "K = 2": round(scores[2], 2), "K = 4": round(scores[4], 2)})
    return pd.DataFrame(rows)


def prose(text):
    st.markdown(text)


st.html('<div style="height:12px"></div><p class="fap-kicker">HOW IT WORKS</p>'
        '<h1 class="fap-display fap-h1" style="font-size:clamp(40px,6vw,64px)">The method, and where it is weak</h1>'
        '<p class="fap-sub">Nothing is scraped live and nothing is trained in the app: every figure is rebuilt by '
        f'<code>python -m src.pipeline</code>. Full detail: <a href="{REPO_URL}/MODULES.md" style="color:#F5A15C">the repo docs</a>.</p>')

st.html(ui.section_title("The data"))
prose(
    f"- **{len(per90):,} players, {per90['competition'].nunique()} leagues.** Every full league season StatsBomb's free tier "
    "has: the Premier League, La Liga, Serie A and Ligue 1 (all 2015/16), and the Frauen-Bundesliga, FA Women's Super "
    "League, Liga F and Serie A Women (all 2023/24) plus the NWSL 2023. A player needs 900 minutes to be counted.\n"
    "- **Shots.** The shot model is trained on the Premier League 2015/16 and Bayer Leverkusen 2023/24 "
    f"({xg['n_train_shots']:,} shots), then tested on {len(tests)} tournaments it never saw. Goals against chances is shown "
    "only for the Premier League 2015/16, the one league that is both in the player pool and in the shot data.\n"
    f"- **Prices.** Transfermarkt values for the men's leagues ({len(pool.market_values):,} matched), around the 2015/16 "
    "season. There is no shared ID with StatsBomb, so a player is matched by name and then must be placed at the same "
    "club that season: no confident match leaves a blank, never a guess. Transfermarkt's open data has no women's football."
)

st.html(ui.section_title("1 · What kind of player: percentiles"))
prose(
    "Each stat is counted per 90 minutes. A player's \"top N%\" ranks his or her **standing within their own league**, "
    "among players in the same position group, rather than the raw rate across all leagues. A raw rate mixes league tempo "
    f"into the ranking: the median outfield man makes {outfield_passes['male']:.1f} progressive passes per 90, the median "
    f"outfield woman {outfield_passes['female']:.1f}. The standing is the "
    "number of standard deviations above or below the league average for that position, ranked. The figure printed next "
    "to each bar stays the real per-90 rate and season total. A stat counts as a standout from the "
    f"{STANDOUT_PERCENTILE:.0%} mark."
)

st.html(ui.section_title("2 · Are the goals real: exact odds"))
prose(
    "Every shot gets a chance of scoring from where and how it was taken (distance, angle, body part, how it was created, "
    "game state). If every shot went in with exactly that chance, a player's goals would follow a known distribution, so the "
    "page can say how often an *average finisher* scores as many from the same chances: \"about one season in 22\". That is "
    "exact, not a normal approximation, which overstates small samples. "
    f"The wording changes at 1 in {1 / UNUSUAL_SEASON:.0f} (\"luck alone could explain it\") and 1 in {1 / RARE_SEASON:.0f} "
    "(\"likely skill\"). Even a 1-in-20 season is expected a few times among ~160 shooters, so the page never says \"proven\". "
    "Two simplifications remain: the chances were fitted on the same shots, which moves goals minus xG by about 0.02 goals per "
    "player, and shots are not independent (a rebound exists only because the first shot missed). "
    "A planned upgrade adds proper uncertainty ranges."
)

st.html(ui.section_title("3 · Who plays like this: lookalikes"))
prose(
    "Within a position group, every player is a point in the space of league-adjusted per-90 stats, and the lookalikes are the "
    "nearest points (straight-line distance). Men's and women's lists are the same ranking split by game, so neither hides "
    "the other. Compare ranks one player on the other's list: top 5 reads as like-for-like and top 25 as similar. Two outfield "
    "players of different positions are measured in a space where position still shows, because a position-relative "
    "score would put an average forward and an average midfielder at the same point. "
    f"\"Cheaper\" means valued at {CHEAPER_RATIO:.0%} of the price or less, and a similar style is not the same level: league, "
    "age and contract all move a price."
)

st.html(ui.section_title("How good is the shot model?", "Tested on tournaments it never saw"))
prose(
    f"ROC-AUC is the chance the model ranks a goal's shot as more dangerous than a miss's (1.0 always, 0.5 a coin flip). On "
    f"UEFA EURO 2024, held out entirely, it scores **{xg['logistic']['test_roc_auc']}**. A guess at the average goal rate scores "
    f"{ladder['no_skill']}, shot geometry alone {ladder['geometry_only']}, and the full model {ladder['full']}, so each addition "
    f"earns its place. Across all {len(tests)} held-out tournaments ({n_test_shots:,} shots, {n_womens_tests} of them women's) the range is "
    f"{tests['roc_auc'].min():.2f} to {tests['roc_auc'].max():.2f}."
)
st.html(ui.score_bars([
    (row.label, row.roc_auc, f"{row.n_shots:,} shots · {'women' if row.gender == 'female' else 'men'}'s")
    for row in tests.itertuples()
]))
st.caption("The bar starts at 0.5, a coin flip: its length is the skill above chance.")
st.dataframe(
    tests[["label", "n_shots", "roc_auc", "brier_score"]].rename(columns={
        "label": "Tournament", "n_shots": "Shots", "roc_auc": "ROC-AUC", "brier_score": "Brier score"}),
    hide_index=True, width="stretch",
)
st.caption("A higher Brier score mostly tracks a higher goal rate in that tournament, not a bias.")

st.html(ui.section_title("How clean are the style groups?"))
prose(
    "Silhouette measures how tightly players cluster (−1 to 1). It is low everywhere, with the best value at K = 2: styles "
    "within a position are a soft continuum, not separate blobs. The page leans on rankings and nearest matches, which "
    "need no hard boundaries, rather than on cluster labels."
)
st.dataframe(silhouettes(), hide_index=True, width="stretch")

st.html(ui.section_title("Limits, stated plainly"))
prose(
    "- **League adjustment is relative, not a strength rating.** It compares each player with his or her own league and assumes "
    "the leagues' distributions have a similar shape. There is no external league-strength data behind it.\n"
    "- **The men's data is one season, 2015/16.** StatsBomb's free data has no newer full men's league season, so the men's "
    "prices and finishing are a decade old. The women's leagues are 2023/24.\n"
    "- **Season totals are small samples.** One season of goals barely separates skill from luck, which is why the page "
    "talks in odds.\n"
    "- **Goalkeepers have no shot-quality model yet.** Save % is a rate over shots on target, not a verdict.\n"
    "- **Names are StatsBomb's.** Players are shown by their popular name where StatsBomb has one, otherwise by the full "
    "registered name.\n"
    "- **Event data only.** No tracking, no off-ball movement, no age."
)
st.page_link("views/home.py", label="← Back to the findings")
