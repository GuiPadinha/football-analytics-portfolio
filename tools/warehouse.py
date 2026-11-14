"""Build and test the dbt + DuckDB layer (warehouse/) in one go.

    python -m tools.warehouse            # dbt build: every model, every test
    python -m tools.warehouse --show     # ...then print the club table

Runs from the repo root, because the sources read `app_data/*.parquet` by relative path. dbt's
`target/` and `logs/` go to the system temp folder, not into the synced Drive working tree. The
database is in memory (warehouse/profiles.yml), so nothing is left behind. Exits non-zero when
a model or test fails, which is what CI keys on.
"""

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WAREHOUSE = REPO / "warehouse"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    scratch = Path(tempfile.gettempdir()) / "fap-dbt"
    os.environ.setdefault("DBT_TARGET_PATH", str(scratch / "target"))
    os.environ.setdefault("DBT_LOG_PATH", str(scratch / "logs"))
    os.environ.setdefault("DBT_SEND_ANONYMOUS_USAGE_STATS", "false")
    os.chdir(REPO)

    from dbt.cli.main import dbtRunner  # imported late: the env vars above must be set first

    dirs = ["--project-dir", str(WAREHOUSE), "--profiles-dir", str(WAREHOUSE)]
    # The models over the raw events need the landed Parquet (python -m src.landing), which is
    # local only. Without it (CI, a fresh clone) they and everything downstream are left out.
    raw_dir = Path(os.environ.get("FAP_CACHE_DIR", REPO / "data" / "cache")) / "raw"
    if (raw_dir / "events").is_dir():
        os.environ.setdefault("FAP_RAW_DIR", raw_dir.as_posix())
    else:
        print(f"No raw layer at {raw_dir}: skipping the models built from raw events.")
        dirs += ["--exclude", "source:raw+"]
    runner = dbtRunner()
    if "--show" in argv:
        # In memory, the tables die with the session, so build and query in the same invocation.
        result = runner.invoke(["build", *dirs])
        if result.success:
            result = runner.invoke(["show", *dirs, "--limit", "20",
                                    "--inline", "select * from {{ ref('team_xg') }} order by xg_diff desc"])
    else:
        result = runner.invoke(["build", *dirs])
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
