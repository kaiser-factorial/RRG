#!/usr/bin/env python3
"""
vp_blinding_lint.py — pre-dispatch blinding gate for the validation pipeline.

The single mechanical check that stands between "package assembled" and
"package sent to a validator model." It enforces the blinding rules defined in
vp_config.yaml so a human cannot accidentally leak the results key or a
stage-forbidden methodology protocol.

Two severities:
    HARD FAIL  -> blocks dispatch (exit code 2)
    FLAG/WARN  -> human must confirm or fix (exit code 0; logged)

Run before EVERY dispatch, EVERY stage, EVERY model. See vp-blinding-lint/SKILL.md
and TOOL_MVP_DESIGN.md sec. 5 for the spec this implements.

Usage:
    python3 vp_blinding_lint.py --package PATH --stage STAGE [options]

    --package PATH     the assembled package folder for one {stage, model} run
    --stage  STAGE     replication | robustness | generalization
    --config PATH      vp_config.yaml (default: alongside this script)
    --repo-root PATH   project root containing DataAnal/ and PANEL_VAL/
                       (default: inferred two levels up from the config)
    --json             emit a machine-readable JSON report to stdout
    --quiet            suppress the human-readable report (still sets exit code)

Exit codes:  0 = PASS (possibly with flags/warnings)   2 = HARD FAIL   1 = usage/IO error
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Finding model
# --------------------------------------------------------------------------- #
HARD_FAIL = "HARD_FAIL"
FLAG = "FLAG"
WARN = "WARN"
SEVERITY_ORDER = {HARD_FAIL: 3, FLAG: 2, WARN: 1}


@dataclass
class Finding:
    check: str
    severity: str
    message: str
    items: list = field(default_factory=list)


@dataclass
class Report:
    package: str
    stage: str
    findings: list = field(default_factory=list)

    def add(self, check, severity, message, items=None):
        self.findings.append(Finding(check, severity, message, items or []))

    @property
    def hard_fails(self):
        return [f for f in self.findings if f.severity == HARD_FAIL]

    @property
    def flags(self):
        return [f for f in self.findings if f.severity == FLAG]

    @property
    def warns(self):
        return [f for f in self.findings if f.severity == WARN]

    @property
    def passed(self):
        return len(self.hard_fails) == 0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
TEXT_EXTS = {".md", ".txt", ".csv", ".tsv", ".json", ".py", ".yaml", ".yml",
             ".html", ".r", ".do", ".tex"}

# Dataset-definition constants that legitimately appear everywhere and must NOT
# be treated as result leaks (sample sizes, factor count, item count, scale max).
DATASET_CONSTANTS = {
    "3133", "3,133", "3003", "3,003", "2074", "2,074", "929", "839",
    "170", "214", "8", "10", "13", "5", "1",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.startswith(".DS_Store"):
            yield p


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def matches_denylist(relpath: str, name: str, patterns) -> str | None:
    """Return the matching denylist pattern, or None."""
    for pat in patterns:
        p = pat.rstrip("/")
        # directory-style entry, e.g. "origin_Fable-5/" or "HIDDEN/"
        if pat.endswith("/"):
            if relpath == p or relpath.startswith(p + "/") or f"/{p}/" in f"/{relpath}":
                return pat
            continue
        # glob (SCORECARD_*, *PROTOCOL*)
        if any(ch in pat for ch in "*?[]"):
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(relpath, pat):
                return pat
            continue
        # bare filename
        if name == pat or relpath == pat or relpath.endswith("/" + pat):
            return pat
    return None


# --------------------------------------------------------------------------- #
# Result-token extraction (for the FLAG-level leak scan)
# --------------------------------------------------------------------------- #
# We extract only values that sit next to a result MARKER in the key (so we get
# the headline effect sizes, not every decimal in a loadings matrix). This keeps
# the scan tight enough to be useful — it is what catches the documented
# "Q12 question text embedded +.44" class of leak — without alarm fatigue.
VALUE = r"[+−\-]?\d?\.\d{2,3}"
MARKER_PATTERNS = [
    re.compile(rf"η²\s*=\s*({VALUE})"),                       # η² = .56
    re.compile(rf"\br\s*=\s*({VALUE})"),                     # r = +.44 / r=0.150
    re.compile(rf"\bd\s*=\s*({VALUE})"),                     # d = .42
    re.compile(rf"\bR\s*=\s*({VALUE})"),                     # quadratic R = .156
    re.compile(rf"\bc\s*=\s*({VALUE})"),                     # congruence c = .93
    re.compile(rf"=\s*({VALUE})\b"),                          # generic "= +.44"
    re.compile(rf"\*\*({VALUE})\*\*"),                        # bolded headline value
]
FSTAT_PATTERN = re.compile(r"\bF\(\s*\d+\s*,\s*\d+\s*\)\s*=\s*\d+(?:\.\d+)?")
# Original-method descriptors — only a concern when method must be HIDDEN.
KEYWORD_TOKENS = [
    "Tucker congruence", "higher-order ML EFA", "balanced accuracy",
    "nonlinearity probe", "quad coef", "congruence coefficient",
]


def _is_dataset_constant(tok: str) -> bool:
    bare = tok.replace("+", "").replace("−", "").replace("-", "").replace(",", "")
    return bare in DATASET_CONSTANTS or bare.replace(".", "") in DATASET_CONSTANTS


def extract_result_tokens(key_root: Path):
    """Pull marker-adjacent result values + F-stats from the results key."""
    numeric = set()
    for p in iter_files(key_root):
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for pat in MARKER_PATTERNS:
            for tok in pat.findall(text):
                tok = tok.strip()
                if _is_dataset_constant(tok):
                    continue
                # drop trivial 0.00 / .00 / 1.00 values (too common to be a leak)
                if re.fullmatch(r"[+−\-]?0?\.0{2,3}", tok) or re.fullmatch(r"[+−\-]?1\.0{2,3}", tok):
                    continue
                numeric.add(tok)
        for m in FSTAT_PATTERN.findall(text):
            numeric.add(m.strip())
    return numeric


def normalize_minus(s: str) -> str:
    return s.replace("−", "-")


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def load_config(cfg_path: Path) -> dict:
    with open(cfg_path) as fh:
        return yaml.safe_load(fh)


def resolve_repo_root(cfg_path: Path, override: str | None) -> Path:
    if override:
        return Path(override).resolve()
    # working project root: $RRG_PROJECT_ROOT → `.rrg_root` marker → a data dir
    # (operator/shared/data, or legacy PANEL_VAL/DataAnal) → the parent.
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


def allowed_patterns_for_stage(cfg: dict, stage: str):
    """Filenames/dirs a package MAY legitimately contain for this stage."""
    allowed_names = set()
    allowed_dirs = set()
    # _all files (basenames)
    for f in cfg.get("files", {}).get("all", []):
        allowed_names.add(Path(f).name)
    # auto-shared subset folder
    subset = cfg.get("files", {}).get("subset", {}).get("path", "")
    if subset:
        allowed_dirs.add(Path(subset.rstrip("/")).name)
    # per-stage required methodology
    per_stage = cfg.get("blinding", {}).get("per_stage_methodology", {})
    for req in per_stage.get(stage, {}).get("require", []):
        allowed_names.add(Path(req).name)
    # stage_specific send_in
    for entry in cfg.get("files", {}).get("stage_specific", []):
        if stage in entry.get("send_in", []):
            allowed_names.add(Path(entry["file"]).name)
    return allowed_names, allowed_dirs


def check_withheld(report, pkg_files, pkg_root, cfg):
    deny = cfg.get("blinding", {}).get("always_withhold", [])
    hits = []
    for p in pkg_files:
        r = rel(p, pkg_root)
        pat = matches_denylist(r, p.name, deny)
        if pat:
            hits.append(f"{r}  (matches withheld pattern '{pat}')")
    if hits:
        report.add("withheld_files", HARD_FAIL,
                   "Package contains withheld files (results key / HIDDEN / scorecards).",
                   hits)
    else:
        report.add("withheld_files", WARN, "No withheld files present. OK", [])


def check_stage_methodology(report, pkg_files, pkg_root, cfg, stage):
    per_stage = cfg.get("blinding", {}).get("per_stage_methodology", {}).get(stage, {})
    require = per_stage.get("require", [])
    forbid = per_stage.get("forbid", [])
    names = {p.name for p in pkg_files}
    rels = {rel(p, pkg_root) for p in pkg_files}

    # forbidden
    f_hits = []
    for p in pkg_files:
        pat = matches_denylist(rel(p, pkg_root), p.name, forbid)
        if pat:
            f_hits.append(f"{rel(p, pkg_root)}  (matches forbidden '{pat}')")
    if f_hits:
        report.add("stage_methodology_forbid", HARD_FAIL,
                   f"Stage '{stage}' forbids these methodology files.", f_hits)

    # required
    missing = []
    for req in require:
        rname = Path(req).name
        if rname not in names:
            missing.append(req)
    if missing:
        report.add("stage_methodology_require", HARD_FAIL,
                   f"Stage '{stage}' requires these methodology files (absent).", missing)
    if not f_hits and not missing:
        detail = "no protocol may be present" if not require else f"required: {', '.join(Path(r).name for r in require)}"
        report.add("stage_methodology", WARN,
                   f"Stage '{stage}' methodology rule satisfied ({detail}). OK", [])


def check_routing(report, pkg_files, pkg_root, cfg, stage):
    allowed_names, allowed_dirs = allowed_patterns_for_stage(cfg, stage)
    deny = cfg.get("blinding", {}).get("always_withhold", [])
    unexpected = []
    for p in pkg_files:
        r = rel(p, pkg_root)
        parts = set(Path(r).parts)
        if parts & allowed_dirs:          # inside an allowed folder (subset)
            continue
        if p.name in allowed_names:       # an allowed top-level file
            continue
        if matches_denylist(r, p.name, deny):  # already reported as withheld
            continue
        # forbidden-by-stage already reported; skip those too
        per_stage = cfg.get("blinding", {}).get("per_stage_methodology", {}).get(stage, {})
        if matches_denylist(r, p.name, per_stage.get("forbid", [])):
            continue
        unexpected.append(r)
    if unexpected:
        report.add("routing", HARD_FAIL,
                   f"Files not on the '{stage}' send-list (unexpected routing).",
                   unexpected)
    else:
        report.add("routing", WARN, "All files match the stage send-list. OK", [])


def check_subset_integrity(report, pkg_root, cfg, repo_root):
    subset_rel = cfg.get("files", {}).get("subset", {}).get("path", "")
    if not subset_rel:
        return
    subset_name = Path(subset_rel.rstrip("/")).name
    src = (repo_root / subset_rel).resolve()
    # find the subset folder inside the package
    pkg_subset = None
    for d in pkg_root.rglob(subset_name):
        if d.is_dir():
            pkg_subset = d
            break
    if pkg_subset is None:
        report.add("subset_integrity", HARD_FAIL,
                   f"Auto-shared '{subset_name}/' folder is missing from the package.", [])
        return
    if not src.exists():
        report.add("subset_integrity", WARN,
                   f"Source subset not found at {subset_rel}; cannot hash-verify.", [])
        return

    # compare file sets + hashes (ignore dotfiles)
    def file_map(base):
        m = {}
        for p in iter_files(base):
            m[str(p.relative_to(base))] = p
        return m

    src_map, pkg_map = file_map(src), file_map(pkg_subset)
    issues = []
    for name in sorted(set(src_map) - set(pkg_map)):
        issues.append(f"missing from package: {subset_name}/{name}")
    for name in sorted(set(pkg_map) - set(src_map)):
        issues.append(f"EXTRA file in package subset (possible leak): {subset_name}/{name}")
    for name in sorted(set(src_map) & set(pkg_map)):
        if sha256(src_map[name]) != sha256(pkg_map[name]):
            issues.append(f"hash mismatch (modified): {subset_name}/{name}")
    if issues:
        report.add("subset_integrity", HARD_FAIL,
                   f"'{subset_name}/' does not match the hash-locked source.", issues)
    else:
        report.add("subset_integrity", WARN,
                   f"'{subset_name}/' matches source ({len(src_map)} files, hashes OK).", [])


def check_result_tokens(report, pkg_files, pkg_root, cfg, repo_root, stage):
    scan = cfg.get("blinding", {}).get("result_token_scan", {})
    key_rel = scan.get("source")
    if not key_rel:
        return
    key_root = (repo_root / key_rel).resolve()
    if not key_root.exists():
        report.add("result_token_scan", WARN,
                   f"Results key not found at {key_rel}; token scan skipped.", [])
        return
    tokens = extract_result_tokens(key_root)
    norm_tokens = {normalize_minus(t): t for t in tokens}
    # The hash-locked subset is verified-identical canonical INPUT (its numbers
    # are the given factor solution / item data, not results) — scanning it is
    # pure noise, and its integrity is separately guaranteed. Skip it here.
    subset_name = Path(cfg.get("files", {}).get("subset", {})
                       .get("path", "validation_subset").rstrip("/")).name
    method_hidden = stage in ("robustness", "generalization")
    hits = []
    for p in pkg_files:
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        r = rel(p, pkg_root)
        if subset_name in Path(r).parts:
            continue
        try:
            text = normalize_minus(p.read_text(errors="ignore"))
        except Exception:
            continue
        found = sorted({orig for norm, orig in norm_tokens.items() if norm and norm in text})
        # method-descriptor keywords only matter where method must be hidden
        kw = [k for k in KEYWORD_TOKENS if k.lower() in text.lower()] if method_hidden else []
        if found or kw:
            sample = (found[:8] + (["…"] if len(found) > 8 else []) + kw[:4])
            hits.append(f"{r}: {', '.join(sample)}")
    if hits:
        report.add("result_token_scan", FLAG,
                   "Possible result tokens from the key appear in package text "
                   "(assistive — a human must confirm each is coincidental).", hits)
    else:
        report.add("result_token_scan", WARN, "No result tokens detected. OK", [])


def check_completeness(report, pkg_files, pkg_root, cfg, stage):
    names = {p.name for p in pkg_files}
    required = [Path(f).name for f in cfg.get("files", {}).get("all", [])]
    per_stage = cfg.get("blinding", {}).get("per_stage_methodology", {}).get(stage, {})
    required += [Path(r).name for r in per_stage.get("require", [])]
    missing = [r for r in required if r not in names]
    if missing:
        report.add("completeness", WARN,
                   "Stage's expected files are not all present.", missing)
    else:
        report.add("completeness", WARN, "All expected files present. OK", [])


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run_lint(package: Path, stage: str, cfg: dict, repo_root: Path) -> Report:
    report = Report(package=str(package), stage=stage)
    pkg_files = list(iter_files(package))
    if not pkg_files:
        report.add("package", HARD_FAIL, f"Package folder is empty or missing: {package}", [])
        return report
    check_withheld(report, pkg_files, package, cfg)
    check_stage_methodology(report, pkg_files, package, cfg, stage)
    check_routing(report, pkg_files, package, cfg, stage)
    check_subset_integrity(report, package, cfg, repo_root)
    check_result_tokens(report, pkg_files, package, cfg, repo_root, stage)
    check_completeness(report, pkg_files, package, cfg, stage)
    return report


def print_report(report: Report):
    line = "=" * 70
    print(line)
    print(f" vp-blinding-lint   stage={report.stage}")
    print(f" package: {report.package}")
    print(line)
    icon = {HARD_FAIL: "✗ HARD FAIL", FLAG: "⚑ FLAG", WARN: "· ok/warn"}
    for f in sorted(report.findings, key=lambda x: -SEVERITY_ORDER[x.severity]):
        print(f"[{icon[f.severity]:>11}] {f.check}: {f.message}")
        for it in f.items:
            print(f"               - {it}")
    print(line)
    if report.passed:
        verdict = "PASS"
        if report.flags:
            verdict += f"  ({len(report.flags)} flag(s) need human confirmation)"
        print(f" RESULT: {verdict}")
    else:
        print(f" RESULT: HARD FAIL — {len(report.hard_fails)} blocking issue(s). "
              f"Dispatch blocked.")
    print(line)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Blinding gate for the validation pipeline.")
    ap.add_argument("--package", required=True, help="assembled package folder")
    ap.add_argument("--stage", required=True,
                    choices=["replication", "robustness", "generalization"])
    here = Path(__file__).resolve().parent
    ap.add_argument("--config", default=str(here / "vp_config.yaml"))
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.stderr.write(f"config not found: {cfg_path}\n")
        return 1
    cfg = load_config(cfg_path)
    repo_root = resolve_repo_root(cfg_path, args.repo_root)
    package = Path(args.package).resolve()

    report = run_lint(package, args.stage, cfg, repo_root)

    if args.json:
        print(json.dumps({
            "package": report.package, "stage": report.stage,
            "passed": report.passed,
            "hard_fails": [asdict(f) for f in report.hard_fails],
            "flags": [asdict(f) for f in report.flags],
            "warns": [asdict(f) for f in report.warns],
        }, indent=2, ensure_ascii=False))
    elif not args.quiet:
        print_report(report)

    return 0 if report.passed else 2


if __name__ == "__main__":
    sys.exit(main())
