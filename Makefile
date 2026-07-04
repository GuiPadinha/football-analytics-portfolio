# Thin wrapper around src/pipeline.py (see its docstring) — the headless, non-notebook
# rebuild: ingestion -> features -> models -> outputs -> manifest/metrics.json.
# `make` isn't required: `python -m src.pipeline` works standalone on any platform.

.PHONY: pipeline pipeline-force test clean

pipeline:
	python -m src.pipeline

pipeline-force:
	python -m src.pipeline --force

test:
	MPLBACKEND=Agg pytest -q

clean:
	rm -f outputs/*.png
