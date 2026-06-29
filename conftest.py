"""Pytest bootstrap: put the project root on sys.path so `import src...` resolves in tests,
regardless of pytest's import mode or where it's invoked from.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
