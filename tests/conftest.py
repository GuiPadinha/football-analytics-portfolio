"""Pytest bootstrap (lives in tests/ to keep the repo root uncluttered).

1. Put the project root on sys.path so `import src...` resolves in tests, regardless of pytest's
   import mode or where it's invoked from.
2. Force matplotlib's headless Agg backend before any test imports pyplot. On a machine whose
   default is a GUI backend (TkAgg on this Windows install), a figure drawn by one test and
   garbage-collected on a Streamlit AppTest thread aborts the whole process (Windows fatal
   exception 0x80000003). That used to be masked only because test_visualisation.py set Agg at
   import time, so a run that didn't collect that file crashed (found 2026-10-02).
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
