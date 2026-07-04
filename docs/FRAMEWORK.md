# The Player Evaluation Framework

Defines what this project does, for whom, and the scope boundary between Module A and Module B.
Read this first if the rest of the repo reads like a pile of loosely related notebooks.

---

## Summary

A recruitment-led player evaluation tool: **given a player, find statistically similar players
(scouting), and separately check whether any player's goal output is real or just variance
(valuation).**

---

## Target User

A **recruitment / data analyst at a club or data provider**, making a signing or squad-planning
decision and wanting evidence rather than reputation. Not a developer — they think in players,
roles, and budgets, not in DataFrames.

The two questions they actually ask, and which module answers each:

| The user asks… | Module | What it is |
|---|---|---|
| "Who else plays like this player — ideally cheaper or younger?" | **B — Similarity** | Scouting lens |
| "This striker scored 20 — is he actually that good, or did he get lucky?" | **A — xG** | Valuation lens |

---

## Module B — Similarity (the Scouting Lens)

The only module where the user provides input: a player name (+ their team, since names aren't
unique).

- **What happens:** every other player in the same position group is ranked by how close their
  per-90 statistical profile is to the target's, in standardised feature space.
- **Output:** a ranked "players like X" list, a style **archetype** label (which of the play-style
  clusters they fall into), and a **radar chart** of their profile against their position peers.
- **Decision it informs:** a like-for-like replacement for a departing player, a cheaper/less-hyped
  alternative to an expensive transfer target, or simply what *kind* of player an unfamiliar name is.

It does not know transfer fees, age, or contracts — it matches on *playing style from on-pitch
output* only. Pairing its shortlist with budget/age filters is a human step (and a candidate
front-end feature).

## Module A — xG (the Valuation Lens)

No user input here — it's pointed at a player/team/season that already exists in the data.

- **What happens:** each shot gets a goal probability from its circumstances (location, angle, body
  part, what created it, game state). Summed per player, that's their **expected goals (xG)**.
- **Output:** **goals minus xG** per player. Positive = scoring more than the chances deserved
  (finishing hot — likely partly luck, expect regression). Negative = scoring less than the chances
  deserved (possibly unlucky — a potential buy-low).
- **Decision it informs:** don't overpay for a player riding a finishing streak; don't write off a
  player who's been creating good chances but not converting.

It is not a scouting tool — it evaluates output that already exists, it doesn't find new players.

---

## How the Modules Combine

> A club's striker is leaving. The analyst needs a replacement on a smaller budget.
>
> 1. **Similarity (B):** input the departing striker → get 5 statistically similar forwards.
> 2. **Valuation (A):** for each of the 5, check goals-minus-xG. One scored 18 last season but is
>    +8 over his xG — a finishing spike likely to regress. Another scored 11 but is −4 under his
>    xG — creating chances he's been unlucky not to finish.
> 3. **Shortlist:** the analyst flags the second player as the better-value target — similar
>    profile, output *suppressed* by variance rather than inflated by it — and discounts the first.
>
> Similarity narrows the field by *style*; xG corrects for *luck*. Neither answers the question
> alone — that's why they're one framework.

---

## Inputs vs. Derived Data

- **Input by the user:** a player name (Module B only). Optionally, which competition/season to
  scope to.
- **Derived by the pipeline:** all features (per-90 metrics, shot geometry), all model outputs
  (xG, clusters, similarity rankings), all charts. None of it is hand-entered.

---

## Out of Scope

- **Youth scouting.** The open data is senior professional matches. There is no data on academy or
  lower-league prospects, so "find the next wonderkid" is not something this can do today — it
  would require a dataset containing those players first, a data decision rather than a model one.
- **Live / in-match prediction.** Everything is post-hoc on completed matches.
- **Biometric / physical load at the player level fused with events.** The StatsBomb (events) and
  SkillCorner (physical tracking) datasets share zero players, so physical and event metrics are
  demonstrated separately, not fused per player. A club's internal data would have both for one
  roster; public data does not.
- **Transfer-fee / market-value modelling.** Out of scope; the tool informs a human's valuation,
  it doesn't price players.

---

## Product Layer (Planned)

Today this lives in notebooks: run cells, read tables. The intended experience is a single screen:

```
[ pick a player ▾ ]  →   ┌─────────────────────────────────────────┐
                         │  Radar (vs. position peers)              │
                         │  "Players like X"  (ranked, with dist.)  │
                         │  xG over/underperformance (is it real?)  │
                         └─────────────────────────────────────────┘
```

That interactive layer (Phase 8 of the hardening initiative) turns a set of analyses into a tool,
and its absence is the main reason the project can currently feel abstract.

The full interface design — screens, interaction model, the map from each panel to the existing
`src/` function that powers it, tech choice (Streamlit), and mockups — is specified in
[PRODUCT_SPEC.md](PRODUCT_SPEC.md). Spec is done; the build is a later session.

---

*Scope, framing, and roadmap for the ongoing improvement work live in [INITIATIVE.md](INITIATIVE.md).*
