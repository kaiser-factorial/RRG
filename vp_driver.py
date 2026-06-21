#!/usr/bin/env python3
"""
vp_driver.py — the thin driver for the validation pipeline (MVP).

Does the deterministic, error-prone file ops so a human doesn't have to:
  1. resolves the {stage, model} run against the roster in vp_config.yaml
     (enforces the Anthropic-as-validator exclusion; records type/license);
  2. assembles the outgoing package by copying the routed files (the `_all`
     files, the hash-locked subset, and the stage's methodology per the
     send-list) into  package_out/{stage}/{label}/ ;
  3. runs the blinding linter (vp_blinding_lint) and REFUSES to proceed on a
     HARD FAIL (override only with --force, which is logged);
  4. creates the validator's output folder — OUTSIDE the package, so returned
     results can never co-mingle with inputs (the contamination gotcha);
  5. writes a provenance record (files sent + sha256 hashes, prompt version,
     timestamp, lint result, determinism settings).

It does NOT run the model or grade — execution happens in the vendor's native
agent app (paste the stage prompt + attach the package); grading is vp-scorecard.

Usage:
    python3 vp_driver.py --stage STAGE --model NAME [options]

    --stage   replication | robustness | generalization
    --model   a model name from the stage roster (substring match ok,
              e.g. "Gemini", "GPT-5.5", "Nemotron")
    --label   folder-safe name for this run (default: derived from --model)
    --config  vp_config.yaml (default: alongside this script)
    --repo-root PATH   project root (default: inferred two levels up from config)
    --dry-run          assemble + lint + report, but write nothing permanent
    --force            proceed past a HARD FAIL (logged as an override; use only
                       with explicit human approval)
    --json             emit a machine-readable run record to stdout

Exit codes: 0 = package built + lint PASS (or forced)   2 = blocked by lint   1 = usage/config error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(1)

# Reuse the linter as a library (same directory).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_blinding_lint as linter  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _force_writable(func, path, _exc):
    """rmtree onerror: clear read-only bits and retry (mounted FS can be picky)."""
    import os
    import stat
    try:
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        func(path)
    except Exception:
        pass


def safe_rmtree(path: Path):
    if path.exists():
        shutil.rmtree(path, onerror=_force_writable)


def normalize_perms(root: Path):
    """Make an assembled package fully removable later (dirs 755, files 644)."""
    import os
    for p in root.rglob("*"):
        try:
            os.chmod(p, 0o755 if p.is_dir() else 0o644)
        except Exception:
            pass
    try:
        os.chmod(root, 0o755)
    except Exception:
        pass


def safe_label(model: str) -> str:
    """Folder-safe label: 'Gemini (confirm flagship)' -> 'Gemini'."""
    base = re.split(r"[\(/]", model)[0].strip()
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_") or "model"


def load_config(cfg_path: Path) -> dict:
    with open(cfg_path) as fh:
        return yaml.safe_load(fh)


def resolve_repo_root(cfg_path: Path, override) -> Path:
    if override:
        return Path(override).resolve()
    import os
    env = os.environ.get("RRG_PROJECT_ROOT")
    if env:
        return Path(env).resolve()
    p = cfg_path.resolve().parent
    for cand in [p, *p.parents]:
        if (cand / ".rrg_root").exists():
            return cand
    markers = ("operator", "shared", "data", "PANEL_VAL", "DataAnal")
    for cand in [p, *p.parents]:
        if any((cand / m).is_dir() for m in markers):
            return cand
    return p.parent


def find_roster_entry(cfg, stage, model):
    """Match --model against the stage roster (exact, then case-insensitive substring)."""
    roster = cfg.get("roster", {}).get(stage, [])
    m = model.strip().lower()
    for e in roster:
        if e.get("model", "").strip().lower() == m:
            return e
    for e in roster:
        name = e.get("model", "").lower()
        if m in name or safe_label(e.get("model", "")).lower() == m:
            return e
    return None


def stage_cfg(cfg, stage):
    for s in cfg.get("stages", []):
        if s.get("id") == stage:
            return s
    return {}


# --------------------------------------------------------------------------- #
# Package assembly
# --------------------------------------------------------------------------- #
def resolve_send_list(cfg, stage, repo_root):
    """Turn the stage's symbolic `send` tokens into concrete source paths.

    Tokens: 'all' -> files.all; 'subset' -> files.subset.path (a folder);
    an explicit path string -> that file; 'subset_newdata' -> TBD (generalization).
    Required per-stage methodology files are unioned in defensively.
    """
    files_cfg = cfg.get("files", {})
    scfg = stage_cfg(cfg, stage)
    send = scfg.get("send", [])
    resolved_files, resolved_dirs, unresolved = [], [], []

    def add_path(token):
        p = (repo_root / token).resolve()
        if p.is_dir():
            resolved_dirs.append(p)
        elif p.is_file():
            resolved_files.append(p)
        else:
            unresolved.append(token)

    for token in send:
        if token == "all":
            for f in files_cfg.get("all", []):
                add_path(f)
        elif token == "subset":
            sub = files_cfg.get("subset", {}).get("path")
            if sub:
                add_path(sub)
        elif token == "subset_newdata":
            unresolved.append("subset_newdata (Stage-3 data plan not set)")
        else:
            add_path(token)

    # Defensive union: per-stage required methodology must be present.
    per_stage = cfg.get("blinding", {}).get("per_stage_methodology", {}).get(stage, {})
    for req in per_stage.get("require", []):
        # find the source: stage_specific entry, else search known roots
        src = None
        for entry in files_cfg.get("stage_specific", []):
            if Path(entry["file"]).name == Path(req).name:
                src = (repo_root / entry["file"]).resolve()
        if src is None:
            # try operator root
            oproot = files_cfg.get("operator_root") or cfg.get("paths", {}).get("operator_root", "PANEL_VAL")
            cand = (repo_root / oproot / req).resolve()
            src = cand
        if src.is_file() and src not in resolved_files:
            resolved_files.append(src)
        elif not src.is_file():
            unresolved.append(f"required methodology not found: {req}")

    return resolved_files, resolved_dirs, unresolved


def assemble_package(pkg_dir: Path, files, dirs):
    safe_rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True)
    manifest = []
    for f in files:
        dst = pkg_dir / f.name
        shutil.copyfile(f, dst)          # content only — don't inherit source perms
        manifest.append((f.name, sha256(dst)))
    for d in dirs:
        dst = pkg_dir / d.name
        shutil.copytree(d, dst, copy_function=shutil.copyfile)
        for p in sorted(dst.rglob("*")):
            if p.is_file() and not p.name.startswith(".DS_Store"):
                manifest.append((str(p.relative_to(pkg_dir)), sha256(p)))
    normalize_perms(pkg_dir)
    return manifest


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="Thin driver for the validation pipeline.")
    ap.add_argument("--stage", required=True,
                    choices=["replication", "robustness", "generalization"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--label", default=None)
    here = Path(__file__).resolve().parent
    ap.add_argument("--config", default=str(here / "vp_config.yaml"))
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.stderr.write(f"config not found: {cfg_path}\n")
        return 1
    cfg = load_config(cfg_path)
    repo_root = resolve_repo_root(cfg_path, args.repo_root)
    stage, model = args.stage, args.model
    label = args.label or safe_label(model)

    log = []  # human-readable trace

    # 1. Resolve roster entry + constraints --------------------------------
    entry = find_roster_entry(cfg, stage, model)
    excluded = [v.lower() for v in cfg.get("constraints", {}).get("exclude_as_validator", [])]
    if entry is None:
        log.append(f"⚠  '{model}' not found in the {stage} roster — proceeding, "
                   f"but type/license won't be recorded. Confirm it belongs in this stage.")
        vendor, mtype, license_ = None, None, None
    else:
        vendor = entry.get("vendor")
        mtype = entry.get("type")
        license_ = entry.get("license")
        if vendor and vendor.lower() in excluded:
            sys.stderr.write(
                f"REFUSED: '{model}' (vendor {vendor}) is excluded as a validator "
                f"(origin family). It produced the work under validation.\n")
            return 1
        log.append(f"✓  roster: {entry.get('model')}  [{mtype}, {license_}]")

    # 2. Resolve + assemble package (in deletable sandbox temp) ------------
    # We build + lint in a staging dir we fully control, then PUBLISH to the
    # user's folder only on PASS. So a leaky package never touches their disk —
    # which also sidesteps the append-only mount (deletes there are blocked).
    files, dirs, unresolved = resolve_send_list(cfg, stage, repo_root)
    if unresolved:
        sys.stderr.write("Cannot assemble package — unresolved send-list items:\n")
        for u in unresolved:
            sys.stderr.write(f"  - {u}\n")
        return 1

    package_out = cfg.get("paths", {}).get("package_out", "PANEL_VAL/_packages")
    staging = Path(tempfile.mkdtemp(prefix="vp_pkg_"))
    pkg_dir = staging / f"{stage}_{label}"
    manifest = assemble_package(pkg_dir, files, dirs)
    log.append(f"✓  package staged ({len(manifest)} files)")

    # 3. Blinding linter — gate --------------------------------------------
    report = linter.run_lint(pkg_dir, stage, cfg, repo_root)
    lint_result = "pass" if report.passed else "hard_fail"
    if report.passed:
        log.append(f"✓  blinding lint: PASS"
                   + (f"  ({len(report.flags)} flag(s) to confirm)" if report.flags else ""))
    else:
        log.append(f"✗  blinding lint: HARD FAIL ({len(report.hard_fails)} blocking issue(s))")
        for f in report.hard_fails:
            log.append(f"      - {f.check}: {f.message}")
            for it in f.items[:8]:
                log.append(f"          · {it}")
    for f in report.flags:
        log.append(f"   ⚑ {f.check}: {f.message}")
        for it in f.items[:8]:
            log.append(f"          · {it}")

    blocked = (not report.passed) and (not args.force)
    if blocked:
        log.append("→  DISPATCH BLOCKED. Fix the issues above, or re-run with --force "
                   "(explicit human override; will be logged).")
    elif not report.passed and args.force:
        log.append("→  HARD FAIL OVERRIDDEN via --force (logged). Confirm this is intentional.")

    # 4. Output folder + publish destination -------------------------------
    scfg = stage_cfg(cfg, stage)
    out_tmpl = scfg.get("output_folder", "{MODEL}/").replace("{MODEL}", label).rstrip("/")
    # honor on-disk convention: ensure the stage is identifiable in the folder name
    if stage not in out_tmpl.lower():
        out_tmpl = f"{stage}_{out_tmpl}"
    operator_root = cfg.get("paths", {}).get("operator_root", "PANEL_VAL")
    output_folder = (repo_root / operator_root / out_tmpl).resolve()
    report_name = scfg.get("report_name", "{MODEL}_Report.docx").replace("{MODEL}", label)

    # publish dir (collision-safe: the mount can't be overwritten/deleted)
    dest = (repo_root / package_out / stage / label).resolve()
    if dest.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = dest.with_name(f"{label}__{stamp}")

    # 5. Provenance --------------------------------------------------------
    prompt_doc = scfg.get("prompt_doc")
    prompt_version = None
    if prompt_doc:
        pd = (repo_root / prompt_doc).resolve()
        prompt_version = {"doc": prompt_doc,
                          "sha256": sha256(pd) if pd.is_file() else None}
    provenance = {
        "stage": stage,
        "model": entry.get("model") if entry else model,
        "label": label,
        "type": mtype, "vendor": vendor, "license": license_,
        "files_sent": [m[0] for m in manifest],
        "file_hashes": {m[0]: m[1] for m in manifest},
        "prompt_version": prompt_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "blinding_lint_result": lint_result,
        "blinding_flags": [f.check for f in report.flags],
        "forced_override": bool(not report.passed and args.force),
        "determinism": cfg.get("constraints", {}).get("determinism", {}),
        "output_folder": str(output_folder),
        "report_name": report_name,
        "package_dir": str(dest),
    }

    if not args.dry_run and not blocked:
        # write provenance into the staged copy, then publish the whole package
        (pkg_dir / "_provenance.json").write_text(json.dumps(provenance, indent=2))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pkg_dir, dest, copy_function=shutil.copyfile)
        log.append(f"✓  package published: {dest}  ({len(manifest)} files)")
        output_folder.mkdir(parents=True, exist_ok=True)
        log.append(f"✓  output folder ready (for returned results): {output_folder}")
        runs_log = (repo_root / package_out / "provenance_log.jsonl").resolve()
        runs_log.parent.mkdir(parents=True, exist_ok=True)
        with open(runs_log, "a") as fh:
            fh.write(json.dumps(provenance) + "\n")
        log.append(f"✓  provenance written: {dest / '_provenance.json'}")
    elif args.dry_run:
        log.append("·  dry-run: package validated; nothing published to your folder.")
    else:
        log.append("·  BLOCKED: package was built only in sandbox staging and never "
                   "published to your folder.")

    safe_rmtree(staging)  # staging is sandbox tmp (deletable); always clean up

    # ---- report ----
    if args.json:
        print(json.dumps({"blocked": blocked, "lint": lint_result,
                          "provenance": provenance, "log": log}, indent=2))
    else:
        line = "=" * 70
        print(line)
        print(f" vp-driver   stage={stage}  model={provenance['model']}  label={label}")
        print(line)
        for l in log:
            print(" " + l)
        print(line)
        if blocked:
            print(" RESULT: BLOCKED — no package dispatched.")
        else:
            print(" RESULT: READY — paste the stage prompt + attach the package, "
                  "then save\n         returned results into the output folder above.")
        print(line)

    return 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
