"""Keep the live app's imported code in step with the files on disk after a deploy.

Why this exists: on Streamlit Cloud a push updates the files in place, and the running process
keeps the modules it already imported in `sys.modules`. Twice on 2026-11-12 a new page ran
against an old `views/data.py` / `src/profile.py` and died with an `ImportError`, while CI was
green, until the app was rebooted by hand (docs/ML_TOOLING.md). `app.py` runs on every rerun, so
it can compare a cheap fingerprint of the shared code (file sizes and modification times) with
the one it saw last, and when they differ drop the project's modules from `sys.modules`. The
next `import` then reads the new files, which is what a reboot achieved.
"""

import sys
from pathlib import Path

# Packages whose modules the pages import and that a push can change underneath them.
SHARED_PACKAGES = ("src", "views")
# Data the cached loaders read: a change here should also empty Streamlit's data cache.
DATA_DIR = "app_data"


def code_fingerprint(root: Path) -> tuple:
    """Return (path, size, mtime_ns) for every shared .py file and app_data file under `root`.

    Stat calls only, no reads: about thirty files, so it is cheap enough for every rerun.
    Sorted, so two calls on unchanged files compare equal.
    """
    files = [p for pkg in SHARED_PACKAGES for p in (root / pkg).glob("*.py")]
    files += [p for p in (root / DATA_DIR).glob("*") if p.is_file()]
    entries = []
    for path in files:
        try:
            stat = path.stat()
        except FileNotFoundError:  # deleted between glob and stat, mid-deploy
            continue
        entries.append((path.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns))
    return tuple(sorted(entries))


def purge_project_modules(modules: dict | None = None) -> list[str]:
    """Remove the project's packages and their submodules from `modules` (default sys.modules).

    Returns the names removed, sorted, so the caller can log what was refreshed. Third-party
    modules are left alone: only a push to this repo can change ours.
    """
    modules = sys.modules if modules is None else modules
    names = [
        name
        for name in modules
        if any(name == pkg or name.startswith(pkg + ".") for pkg in SHARED_PACKAGES)
    ]
    for name in names:
        del modules[name]
    return sorted(names)
