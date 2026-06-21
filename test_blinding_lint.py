#!/usr/bin/env python3
"""
test_blinding_lint.py — reproducible behavior tests for vp_blinding_lint.py.

Builds a clean package and seven deliberately-leaky variants from the real
project files, then asserts the linter's verdict (PASS / HARD FAIL) and which
check fired for each. Run from anywhere:

    python3 test_blinding_lint.py            # uses the project tree two levels up
    python3 test_blinding_lint.py --repo-root /path/to/LS_Lab

Exit code 0 = all tests passed; 1 = a test failed.
No third-party deps beyond what the linter itself needs (PyYAML).
"""
from __future__ import annotations
import argparse
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

LINT = HERE / "vp_blinding_lint.py"


def lint(pkg: Path, stage: str, repo_root: Path):
    """Run the linter, return (passed, hard_checks, flag_checks)."""
    import json
    out = subprocess.run(
        [sys.executable, str(LINT), "--package", str(pkg), "--stage", stage,
         "--repo-root", str(repo_root), "--json"],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout)
    hard = {f["check"] for f in data["hard_fails"]}
    flag = {f["check"] for f in data["flags"]}
    return data["passed"], hard, flag, out.returncode


def build_clean(dst: Path, repo: Path, stage: str):
    panel = repo / "DataAnal/PANEL"
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("STUDY_OVERVIEW_all.md", "INVEST_Qs_OG_all.md", "DYFA_Guidelines_all.pdf"):
        shutil.copy(panel / f, dst / f)
    shutil.copytree(panel / "validation_subset", dst / "validation_subset")
    if stage == "replication":
        shutil.copy(repo / "RRG/prompts/ANALYSIS_PROTOCOL_OG.md", dst / "ANALYSIS_PROTOCOL_OG.md")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(_proj_root()))
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()

    tmp = Path(tempfile.mkdtemp(prefix="vp_lint_test_"))
    failures = []

    def check(name, cond):
        status = "ok " if cond else "FAIL"
        print(f"  [{status}] {name}")
        if not cond:
            failures.append(name)

    try:
        # ---- clean baselines ----
        repl = build_clean(tmp / "clean_repl", repo, "replication")
        rob = build_clean(tmp / "clean_robust", repo, "robustness")

        p, h, f, rc = lint(repl, "replication", repo)
        print("clean replication:")
        check("passes (no hard fails)", p and rc == 0)

        p, h, f, rc = lint(rob, "robustness", repo)
        print("clean robustness:")
        check("passes (no hard fails)", p and rc == 0)
        check("no spurious flags on clean subset", "result_token_scan" not in f)

        # ---- LEAK 1: results key dropped in ----
        d = tmp / "leak_key"; shutil.copytree(rob, d)
        shutil.copytree(repo / "PANEL_VAL/origin_Fable-5", d / "origin_Fable-5")
        p, h, f, rc = lint(d, "robustness", repo)
        print("leak: results key present:")
        check("hard-fails on withheld_files", "withheld_files" in h and rc == 2)

        # ---- LEAK 2: a SCORECARD present ----
        d = tmp / "leak_score"; shutil.copytree(rob, d)
        shutil.copy(HERE / "examples/SCORECARD_robustness_GPT-5.5_v2.md", d / "SCORECARD_x.md")
        p, h, f, rc = lint(d, "robustness", repo)
        print("leak: scorecard present:")
        check("hard-fails on withheld_files", "withheld_files" in h)

        # ---- LEAK 3: OG protocol sent into robustness ----
        d = tmp / "leak_proto"; shutil.copytree(rob, d)
        shutil.copy(repo / "RRG/prompts/ANALYSIS_PROTOCOL_OG.md", d / "ANALYSIS_PROTOCOL_OG.md")
        p, h, f, rc = lint(d, "robustness", repo)
        print("leak: protocol in robustness (method must be hidden):")
        check("hard-fails on stage_methodology_forbid", "stage_methodology_forbid" in h)

        # ---- LEAK 4: replication missing required OG protocol ----
        d = tmp / "miss_proto"; shutil.copytree(rob, d)  # no protocol
        p, h, f, rc = lint(d, "replication", repo)
        print("leak: replication missing required protocol:")
        check("hard-fails on stage_methodology_require", "stage_methodology_require" in h)

        # ---- LEAK 5: extra file slipped into hash-locked subset ----
        d = tmp / "leak_subset"; shutil.copytree(rob, d)
        (d / "validation_subset/NOTES_LEAK.md").write_text("r = +.44 leaked\n")
        p, h, f, rc = lint(d, "robustness", repo)
        print("leak: tampered subset (extra file):")
        check("hard-fails on subset_integrity", "subset_integrity" in h)

        # ---- LEAK 6: result number embedded in _all doc (the Q12 +.44 class) ----
        d = tmp / "leak_token"; shutil.copytree(rob, d)
        with open(d / "INVEST_Qs_OG_all.md", "a") as fh:
            fh.write("\n\nsecurity x exploration composite r = +.44\n")
        p, h, f, rc = lint(d, "robustness", repo)
        print("leak: result value (+.44) in question text:")
        check("flags result_token_scan", "result_token_scan" in f)
        check("flag is assistive — does not hard-block", p and rc == 0)

        # ---- LEAK 7: unexpected operator file (renamed methodology doc) ----
        d = tmp / "leak_route"; shutil.copytree(rob, d)
        shutil.copy(repo / "RRG/prompts/REPLICATION_RUBRIC.md", d / "EXTRA.md")
        p, h, f, rc = lint(d, "robustness", repo)
        print("leak: unexpected file not on send-list:")
        check("hard-fails on routing", "routing" in h)

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
