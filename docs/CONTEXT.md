# Project Context — Owner, Goals, Career

→ [CLAUDE.md](../CLAUDE.md)

---

## Owner

**Guilherme Padinha**
- Data Engineer / Consultant, ~3 years experience, based in Lisbon
- Stack: Python, SQL, Scala, Databricks, Hadoop, HBase, Git, CI/CD
- Strong in pipeline engineering and ETL; solid theoretical ML, limited hands-on ML practice
- Semi-professional football background (forward/winger, 2008–2018); currently active in amateur league
- Applying to: Premier League clubs, La Liga clubs, Bundesliga clubs, Football Radar, StatsBomb, Opta

---

## Learning Goals

**This project's primary purpose is for Guilherme to learn and practice hands-on ML**, not just produce a portfolio artifact. The portfolio is the by-product; the understanding is the point.

How this changes Claude Code's behavior:
- **Narrate the "why" behind every modelling decision** — why this train/test split, why this metric, why this model. A working notebook with no explained reasoning fails the actual goal.
- **Surface tradeoffs and negative results honestly** — "I tried X, it didn't beat the baseline, here's why" is more valuable than quietly picking whichever number looks best.
- **Flag real ML/stats gotchas when they come up** — these are exactly the things hard to learn from reading alone.
- **When Guilherme asks "why" or seems unsure, slow down and explain** before writing more code.

### The two-module ML curriculum

| Module | ML paradigm | Core skills |
|---|---|---|
| **A — xG model** | Supervised, binary classification | Feature engineering, baseline-before-complexity, calibration vs. discrimination, train/test under distribution shift |
| **B — Player similarity** | Unsupervised, clustering + PCA | Feature scaling, K-means, PCA, judging cluster quality without ground-truth labels |

---

## Career Context

Target roles being applied to in parallel:
- Data Engineer / Analytics Engineer at football clubs (PL, Bundesliga, La Liga)
- Data Scientist at Football Radar (London) — requires production ML experience
- Data Analyst at StatsBomb, Opta, Hudl

This project is the primary portfolio differentiator. Will be linked on GitHub (public repo), LinkedIn under Projects, and CV under a dedicated Projects section.

**Key gap addressed:** no prior public football data work despite strong engineering background and genuine football domain knowledge.

---

## Portfolio Framing

When writing README sections, docstrings, or any public-facing text:
- Frame Module A + B together as a **"Player Evaluation Framework"** — the same framing used by Football Radar in their Club Services job descriptions
- Emphasise both: data engineering rigour (clean pipelines, reproducibility) AND analytical insight
- Always include a "so what" — not just what the model does, but what decision it informs
- Avoid academic language; write as if explaining to a **sporting director**, not a reviewer
- Avoid Messi-era La Liga as primary dataset — overdone in public portfolios, weak differentiation
- Ronaldo and Messi as obviously outliers — worth mentioning for benchmarking (the era was genuinely exceptional, which makes their feats even more absurd)
- True biometric data (HRV, sleep, muscle recovery) is never publicly released — legally/contractually protected by clubs; SkillCorner physical tracking is the realistic public-facing equivalent
