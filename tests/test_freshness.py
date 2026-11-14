"""Tests for src/freshness.py: the stale-module guard app.py runs on every rerun."""

import os

from src.freshness import code_fingerprint, purge_project_modules


def _tree(tmp_path):
    for pkg in ("src", "views", "app_data"):
        (tmp_path / pkg).mkdir()
    (tmp_path / "src" / "profile.py").write_text("x = 1\n")
    (tmp_path / "views" / "data.py").write_text("y = 1\n")
    (tmp_path / "app_data" / "players.parquet").write_bytes(b"abc")
    return tmp_path


def test_fingerprint_is_stable_when_nothing_changes(tmp_path):
    root = _tree(tmp_path)
    assert code_fingerprint(root) == code_fingerprint(root)
    assert len(code_fingerprint(root)) == 3


def test_fingerprint_changes_when_a_shared_module_changes(tmp_path):
    root = _tree(tmp_path)
    before = code_fingerprint(root)
    path = root / "src" / "profile.py"
    path.write_text("x = 1\ndef build_your_own(): ...\n")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    assert code_fingerprint(root) != before


def test_fingerprint_changes_when_app_data_changes(tmp_path):
    root = _tree(tmp_path)
    before = code_fingerprint(root)
    (root / "app_data" / "new.parquet").write_bytes(b"x")
    assert code_fingerprint(root) != before


def test_fingerprint_ignores_files_outside_the_shared_packages(tmp_path):
    root = _tree(tmp_path)
    before = code_fingerprint(root)
    (root / "README.md").write_text("hi")
    (root / "src" / "notes.txt").write_text("hi")
    assert code_fingerprint(root) == before


def test_purge_removes_only_project_modules():
    modules = {
        "src": 1, "src.profile": 2, "views": 3, "views.data": 4,
        "pandas": 5, "srcery": 6, "streamlit.views": 7,
    }
    removed = purge_project_modules(modules)
    assert removed == ["src", "src.profile", "views", "views.data"]
    assert set(modules) == {"pandas", "srcery", "streamlit.views"}
