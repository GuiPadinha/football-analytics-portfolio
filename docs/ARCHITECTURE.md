# Architecture — how the pieces fit together

→ [CLAUDE.md](../CLAUDE.md) | Module specs: [MODULES.md](MODULES.md) | Future app's panel→function
map: [PRODUCT_SPEC.md](PRODUCT_SPEC.md)

CLAUDE.md's Repository Layout tells you *what each file is*, one line each. This doc tells you
*how they depend on each other* — the actual import graph, plus the coupling that doesn't show up
in an import graph at all (shared DataFrame schemas). Written because that gap is real: nothing
else in the repo shows the shape of `src/` end-to-end.

---

## The Four Layers

```
Layer 0 — ingestion:       data_loader.py, config.py
Layer 1 — feature build:   features.py (Module A), similarity.py (Module B)
Layer 2 — model/analysis:  models.py                (Module A only — Module B's clustering
                                                       already lives inside similarity.py)
Layer 3 — presentation:    visualisation.py
Layer 4 — orchestration:   manifest.py, metrics.py, pipeline.py
```

Consumers sit outside `src/`: **notebooks/** (the narrated teaching surface — S1–S8 + Phase 2
rigor sections) and **pipeline.py** (the headless, non-notebook twin — see Phase 3d) both call
into the same Layer 1–3 functions. **tests/** exercises the pure functions directly.

---

## Import Graph

| Module | Imports from `src/` | Imported by |
|---|---|---|
| `config.py` | — | `manifest.py`, `metrics.py`, `pipeline.py` |
| `data_loader.py` | — | `features.py`, `similarity.py`, `manifest.py` |
| `features.py` | `data_loader` | `pipeline.py` (+ notebook 02) |
| `similarity.py` | `data_loader` | `metrics.py`, `pipeline.py` (+ notebook 03) |
| `models.py` | — | `metrics.py`, `pipeline.py` (+ notebook 02) |
| `visualisation.py` | — | `pipeline.py` (+ notebooks 02/03) |
| `manifest.py` | `config`, `data_loader` | `pipeline.py` |
| `metrics.py` | `config`, `models`, `similarity` | `pipeline.py` |
| `pipeline.py` | `config`, `features`, `manifest`, `metrics`, `models`, `similarity`, `visualisation` | — (top-level entry point, `python -m src.pipeline`) |

Two things worth noticing, because they're deliberate design choices, not accidents:

**`models.py` and `visualisation.py` import nothing from `src/`.** Both are dataset-agnostic —
`models.py` trains/evaluates on whatever `X`/`y` a caller hands it, `visualisation.py` plots
whatever arrays/DataFrames a caller hands it. Neither knows StatsBomb, `config.py`, or the other's
existence. This is why the same `plot_calibration_curve`/`plot_shot_map` functions work unchanged
whether the caller is notebook 02, `pipeline.py`, or (per [PRODUCT_SPEC.md](PRODUCT_SPEC.md)) a
future Streamlit app.

**`features.py` and `similarity.py` don't import `config.py` either**, even though the whole
project is "about" specific StatsBomb competitions. `build_training_dataset(datasets)` and
`build_player_per90_features(competition_id, season_id)` take plain ids/`Dataset` objects as
*parameters* — the caller decides which competitions to pull. `config.py`'s named constants
(`TRAIN_SETS`, `SIMILARITY_SET`, etc.) only get imported by the **project-specific glue**:
`manifest.py`, `metrics.py`, and `pipeline.py`, which pin down "the ones this project actually
uses" as their *default* argument. Swap in Women's EURO 2025 (Phase 4) by editing `config.py`
and the glue layer — the feature/model/plot functions underneath don't change.

**`data_loader.py` isn't just network I/O** — it also holds `safe_bool_column`/`safe_column`,
small shared helpers for StatsBomb's sparse-column quirk (a flag column is absent entirely from a
match's events if nothing in that match set it). `similarity.py` needed this from the start;
`features.py` didn't need it until Phase 4 added a competition where the gap was real (Barcelona
2020/21 has one match with zero first-time shots) and a bare column access crashed. Both now
import the helpers from `data_loader.py` rather than each defining their own — the fix that
surfaces this kind of latent bug is adding genuinely new data, not re-running the same fixtures.

---

## Data Contracts (Schemas, Not Imports)

An import graph can't show this dependency: two Layer 1 outputs are shaped by their producer and
consumed by column name elsewhere, with no shared type checking anything.

`features.extract_shot_features`/`build_training_dataset` produce a shots table with fixed columns
(`distance_to_goal`, `angle_to_goal`, `game_state_score_diff`, `is_header`, `is_first_time`,
`under_pressure`, `is_penalty`, `is_free_kick`, `assist_type`, `is_goal`, plus
`player`/`team`/`competition_id`). `models.build_feature_matrix` and `build_player_xg_table`
hard-assume exactly these names — renaming a column in `features.py` breaks `models.py` silently
(a `KeyError`, not a type error) until a test or a run catches it.

`similarity.build_player_per90_features` produces `position_group` plus one `<action>_p90` column
per `ACTION_COLUMNS`. `scale_features`, `compute_silhouette_scores`, `fit_kmeans`, and
`metrics.compute_similarity_metrics` all key off `PER90_FEATURE_COLUMNS` — the single place that
list is defined.

Changing either producer's output schema is therefore a cross-cutting change, even though
`git grep "from src.features import"` would show only one file importing it.

---

## Data Flow — Module A (xG)

```
data_loader.load_events (per-match, disk-cached)
        │
        ▼
features.extract_shot_features  ──(build_training_dataset, one Dataset per league/tournament)──►
        │
        ▼  (data/shots_{train,test}.parquet — Parquet cache, Phase 1)
        │
models.build_feature_matrix ──► models.train_logistic_regression / train_gradient_boosting
        │                              │
        ▼                              ▼
models.evaluate_model            models.get_coefficients / get_feature_importance
        │
        ▼
visualisation.plot_calibration_curve / plot_shot_map / plot_player_xg_ranking
```

`metrics.compute_xg_metrics` re-runs this same chain (minus the plots) to produce the headline
numbers written to `metrics.json`; `pipeline.run_xg_pipeline` re-runs it complete with the plots.

## Data Flow — Module B (Similarity)

```
data_loader.load_events / load_lineups / load_matches (per-match, disk-cached)
        │
        ▼
similarity.build_player_per90_features
   (compute_minutes_played → resolve_season_positions, extract_player_match_actions)
        │
        ▼  (data/player_per90_pl_2015_16.pkl — pickle cache, Phase 2)
        │
similarity.scale_features ──► similarity.fit_kmeans (per position group, K=4)
        │                             │
        ▼                             ▼
similarity.compute_silhouette_scores   similarity.run_pca
        │                             │
        ▼                             ▼
visualisation.plot_silhouette_curve   visualisation.plot_pca_clusters
        │
        └──► similarity.find_similar_players ──► visualisation.plot_player_radar
```

`metrics.compute_similarity_metrics` re-runs the scale→silhouette portion (no plots, no
clustering) for the headline numbers; `pipeline.run_similarity_pipeline` re-runs the complete
chain with every plot.

---

## The Pure-Compute / IO-Wrapper Split

`manifest.py` and `metrics.py` both split into two halves on purpose:

- **Pure compute** (`build_manifest`, `compute_xg_metrics`, `compute_similarity_metrics`,
  `build_metrics`) — takes in-memory data (or an *injected* loader function), returns a plain
  dict, touches no disk and no network. This is what `tests/test_manifest.py` and
  `tests/test_metrics.py` exercise, which is why the suite runs offline in CI with no `data/`.
- **IO wrapper** (`write_manifest`, `write_metrics`) — the thin shell that actually reads
  `data/`/hits the network and writes the JSON file. Not unit-tested directly (there's nothing to
  assert beyond "did it call the pure function and write a file"); exercised for real by
  `pipeline.py`'s end-to-end run instead.

`pipeline.py` follows the same instinct at a coarser grain: `build_shot_tables`/
`build_similarity_table` (the only genuinely new logic — decide rebuild-vs-reuse-cache) are unit
tested with monkeypatched builders (`tests/test_pipeline.py`); `run_xg_pipeline`/
`run_similarity_pipeline` are pure orchestration of already-tested Layer 2/3 functions and are
instead verified by actually running the pipeline end-to-end (see Phase 3d's PROGRESS.md entry).

---

## Related Documentation

This doc covers the engineering shape (modules, imports, data flow). For the product shape — which
UI panel a future Streamlit app would power with which function, and the precomputed-artifact data
flow that app would need — see [PRODUCT_SPEC.md](PRODUCT_SPEC.md)'s component→backend map. The two
docs describe the same `src/` from different angles; neither duplicates the other's table.
