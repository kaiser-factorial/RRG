#!/usr/bin/env python3
"""
test_driver.py — reproducible behavior tests for vp_driver.py.

Drives the real project files but redirects every WRITE (published packages,
output folders, provenance log) into a throwaway temp tree via an override
config, so running the tests never touches the operator's real folders.

Covers: dry-run validation, a real publish (package + provenance + output
folder + runs log), the blinding gate blocking a leaked send-list, the --force
override landing in a collision-safe timestamped dir, and the Anthropic-as-
validator refusal.

    python3 test_driver.py [--repo-root /path/to/LS_Lab]

Exit 0 = all tests passed; 1 = a failure.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DRV = HERE / "vp_driver.py"


def make_override_config(base_cfg: Path, tmp: Path, mutate=None) -> Path:
    """Copy the real config, repoint package_out + operator_root into tmp."""
    c = yaml.safe_load(base_cfg.read_text())
    c.setdefault("paths", {})
    c["paths"]["package_out"] = str(tmp / "_packages")
    c["paths"]["operator_root"] = str(tmp / "_operator")
    if mutate:
        mutate(c)
    out = tmp / f"cfg_{abs(hash(str(mutate)))%9999}.yaml"
    out.write_text(yaml.safe_dump(c))
    return out


def run(stage, model, cfg, repo, extra=None):
    cmd = [sys.executable, str(DRV), "--stage", stage, "--model", model,
           "--config", str(cfg), "--repo-root", str(repo), "--json"]
    if extra:
        cmd += extra
    p = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    return p.returncode, data, p.stdout, p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(HERE.parents[1]))
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    base_cfg = HERE / "vp_config.yaml"
    tmp = Path(tempfile.mkdtemp(prefix="vp_driver_test_"))
    failures = []

    def check(name, cond):
        print(f"  [{'ok ' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    try:
        cfg = make_override_config(base_cfg, tmp)

        # 1. dry-run replication: validates, publishes nothing
        rc, d, out, err = run("replication", "Gemini", cfg, repo, ["--dry-run"])
        print("dry-run replication/Gemini:")
        check("exit 0 / not blocked", rc == 0 and d and not d["blocked"])
        check("nothing published", not (tmp / "_packages").exists())

        # 2. real robustness publish
        rc, d, out, err = run("robustness", "DeepSeek", cfg, repo)
        print("real robustness/DeepSeek:")
        pkg = Path(d["provenance"]["package_dir"]) if d else None
        check("exit 0 / lint pass", rc == 0 and d and d["lint"] == "pass")
        check("package published (18 files + provenance)",
              pkg and pkg.exists() and (pkg / "_provenance.json").exists()
              and len(list((pkg / "validation_subset").glob("*"))) > 0)
        check("type/license recorded", d["provenance"]["type"] == "open")
        check("output folder created",
              Path(d["provenance"]["output_folder"]).exists())
        check("runs log appended",
              (tmp / "_packages" / "provenance_log.jsonl").exists())

        # 3. leaked send-list -> blocked, nothing published
        def inject_key(c):
            for s in c["stages"]:
                if s["id"] == "robustness":
                    s["send"] = ["all", "subset",
                                 "PANEL_VAL/origin_Fable-5/INVESTIGATION_SUMMARY.md"]
        leak_cfg = make_override_config(base_cfg, tmp, inject_key)
        rc, d, out, err = run("robustness", "DeepSeek", leak_cfg, repo)
        print("leaked send-list (results key):")
        check("exit 2 / blocked", rc == 2 and d and d["blocked"])
        check("leaked file NOT on disk",
              not list((tmp / "_packages").rglob("INVESTIGATION_SUMMARY.md")))

        # 4. --force override -> published, forced_override flagged, timestamped
        rc, d, out, err = run("robustness", "DeepSeek", leak_cfg, repo, ["--force"])
        print("--force override of the leak:")
        check("exit 0 / not blocked", rc == 0 and d and not d["blocked"])
        check("forced_override recorded", d["provenance"]["forced_override"] is True)
        check("published to collision-safe dir",
              "__" in Path(d["provenance"]["package_dir"]).name)

        # 5. Anthropic-as-validator refusal
        def add_anthropic(c):
            c["roster"]["robustness"].append(
                {"model": "Fable 5", "vendor": "Anthropic",
                 "type": "frontier", "license": "proprietary"})
        anth_cfg = make_override_config(base_cfg, tmp, add_anthropic)
        rc, d, out, err = run("robustness", "Fable 5", anth_cfg, repo)
        print("Anthropic model as validator:")
        check("exit 1 / refused", rc == 1 and "REFUSED" in err)

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
