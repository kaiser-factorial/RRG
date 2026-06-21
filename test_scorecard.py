#!/usr/bin/env python3
"""
test_scorecard.py — reproducible behavior tests for vp_scorecard.py.

Runs the scaffolder against the real GPT-5.5 robustness run vs. the results key,
writing into a temp dir so the real scorecards are never touched, and asserts
the skeleton is structurally faithful and grades NOTHING as final.

    python3 test_scorecard.py [--repo-root /path/to/LS_Lab]
Exit 0 = all passed; 1 = a failure.
"""
from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SC = HERE / "vp_scorecard.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(HERE.parents[1]))
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    run = repo / "PANEL_VAL/robustness_GPT-5.5"
    key = repo / "PANEL_VAL/origin_Fable-5"
    prior = HERE / "SCORECARD_robustness_GPT-5.5_v2.md"
    tmp = Path(tempfile.mkdtemp(prefix="vp_sc_test_"))
    failures = []

    def check(name, cond):
        print(f"  [{'ok ' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    try:
        if not run.is_dir():
            print(f"  [SKIP] real run folder not present: {run}")
            return 0
        cmd = [sys.executable, str(SC), "--run", str(run), "--stage", "robustness",
               "--model", "GPT-5.5", "--license", "proprietary", "--out", str(tmp),
               "--version", "3"]
        if prior.exists():
            cmd += ["--prior", str(prior)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        out = (tmp / "SCORECARD_robustness_GPT-5.5_v3.md")
        print("scaffold real GPT-5.5 run:")
        check("exit 0", p.returncode == 0)
        check("scorecard written", out.exists())
        md = out.read_text() if out.exists() else ""

        score_rows = [l for l in md.splitlines()
                      if re.match(r"^\|\s*\d+\s*\|", l) and "orig Q" in l]
        check("13 question rows mapped", len(score_rows) == 13)
        check("nothing graded as a FINAL verdict",
              sum(1 for l in score_rows
                  if re.search(r"\*\*(REPRODUCED|CONVERGED|DIVERGED)\*\*", l)) == 0)
        check("12 rows PENDING", sum(1 for l in score_rows if "PENDING" in l) == 12)
        check("exactly 1 advisory hint, on Q2",
              sum(1 for l in score_rows if re.search(r"_[A-Z]+\?_", l)) == 1
              and re.search(r"^\|\s*2\s*\|.*_[A-Z]+\?_", score_rows[1]) is not None)
        check("validator material populated for all 13",
              all("not found" not in l for l in score_rows))
        check("header marks every verdict PROVISIONAL",
              "PROVISIONAL" in md and "SKELETON" in md)

        # prior diff
        if prior.exists():
            check("what-changed table seeded with prior verdicts",
                  "What changed from" in md
                  and re.search(r"\| 12 \| REPRODUCED →", md) is not None
                  and re.search(r"\| 13 \| CONVERGED / N-A →", md) is not None)

        # auto-version: with no --version and the temp dir holding v3, next is v4
        p2 = subprocess.run(
            [sys.executable, str(SC), "--run", str(run), "--stage", "robustness",
             "--model", "GPT-5.5", "--out", str(tmp)],
            capture_output=True, text=True)
        check("auto-version increments to v4",
              (tmp / "SCORECARD_robustness_GPT-5.5_v4.md").exists())
        check("auto-detects v3 as prior",
              "prior: SCORECARD_robustness_GPT-5.5_v3.md" in p2.stdout)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} test(s) FAILED: {', '.join(failures)}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
