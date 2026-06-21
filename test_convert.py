#!/usr/bin/env python3
"""
test_convert.py — reproducible behavior tests for convert_data.py.

Uses a small subset .sav (fast) to assert the converter is faithful, multi-
format, and deterministic; also checks a flat (csv) source round-trips. Writes
only into a temp dir.

    python3 test_convert.py [--repo-root /path/to/LS_Lab]
Exit 0 = all passed; 1 = a failure.  Requires pyreadstat + pandas (+ pyarrow for parquet).
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

def _proj_root():
    for c in [HERE, *HERE.parents]:
        if (c / "PANEL_VAL").is_dir() or (c / "DataAnal").is_dir():
            return c
    return HERE.parent

CONV = HERE / "convert_data.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(_proj_root()))
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    candidates = [
        repo / "DataAnal/PANEL/validation_subset/LS_analysis_main_N2074.sav",
        repo / "DataAnal/fullSet/LSS1_Clean_Skopje2_3133Ps_noContacts_ZV_6_8_26_forPascal.sav",
    ]
    sav = next((c for c in candidates if c.exists()), None)
    if sav is None:
        print("  [SKIP] no .sav available"); return 0
    try:
        import pyreadstat  # noqa
        import pandas as pd
    except ImportError:
        print("  [SKIP] pyreadstat/pandas not installed"); return 0
    have_parquet = True
    try:
        import pyarrow  # noqa
    except ImportError:
        have_parquet = False

    tmp = Path(tempfile.mkdtemp(prefix="vp_conv_test_"))
    failures = []

    def check(name, cond):
        print(f"  [{'ok ' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    def run(stem, extra=None):
        return subprocess.run([sys.executable, str(CONV), str(sav),
                               "--out", str(tmp / stem)] + (extra or []),
                              capture_output=True, text=True)

    try:
        fmts = ["csv"] + (["parquet"] if have_parquet else [])
        r1 = run("a", ["--formats"] + fmts + ["--json"])
        print(f"convert (coded, formats={fmts}):")
        check("exit 0", r1.returncode == 0)
        summary = json.loads(r1.stdout) if r1.stdout.strip().startswith("{") else {}
        csv1 = tmp / "a.csv"
        check("csv + sidecar + codebook written",
              csv1.exists() and (tmp/"a.meta.json").exists() and (tmp/"a.codebook.csv").exists())
        check("no pkl produced (dropped)", not (tmp/"a.pkl").exists())
        if have_parquet:
            check("parquet written", (tmp/"a.parquet").exists())
        m = json.loads((tmp/"a.meta.json").read_text())
        check("sidecar: rows/cols + 64-char source hash + dtypes",
              m["n_rows"] > 0 and len(m["source_sha256"]) == 64
              and all("dtype" in v for v in m["variables"].values()))
        check("value labels captured",
              sum(1 for c in m["columns"] if m["variables"][c]["value_labels"]) > 0)

        # VERIFICATION: every derivative identical to the source (within float precision)
        check("all outputs verified identical to source", summary.get("all_verified") is True)
        for o in summary.get("outputs", []):
            v = o["verify"]
            check(f"{o['format']}: identical (diff≤tol, strings exact, NaN ok)",
                  v["ok"] and v["string_mismatches"] == 0 and v["nan_pattern_ok"]
                  and v["max_numeric_diff"] <= v["tolerance"])
        # parquet should be bit-exact
        pq = next((o for o in summary.get("outputs", []) if o["format"] == "parquet"), None)
        if pq:
            check("parquet is bit-for-bit exact", pq["verify"]["exact"] is True)
        check("verification recorded in sidecar", "verification" in m)

        # csv byte-determinism
        run("b", ["--formats", "csv"])
        check("csv byte-identical on re-run", (tmp/"b.csv").read_bytes() == csv1.read_bytes())

        # labeled differs from coded
        run("c", ["--formats", "csv", "--labeled"])
        check("labeled csv differs from coded", (tmp/"c.csv").read_bytes() != csv1.read_bytes())

        # generalized reader: feed the csv we just made back in (flat source, thin meta)
        rc = subprocess.run([sys.executable, str(CONV), str(tmp/"a.csv"),
                             "--out", str(tmp/"d"), "--formats", "csv"],
                            capture_output=True, text=True)
        print("generalized reader (csv source):")
        check("csv source converts", rc.returncode == 0 and (tmp/"d.csv").exists())
        md = json.loads((tmp/"d.meta.json").read_text())
        check("flat source → thin metadata (no value labels)",
              md["source_format"] == ".csv"
              and all(v["value_labels"] is None for v in md["variables"].values()))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} test(s) FAILED: {', '.join(failures)}"); return 1
    print("All tests passed."); return 0


if __name__ == "__main__":
    sys.exit(main())
