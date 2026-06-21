#!/usr/bin/env python3
"""
vp_scorecard.py — build a validation-scorecard SKELETON for a validator run.

Operationalizes Stage 6 (Grading). It does the tedious, mechanical assembly so
a human can grade fast:
  - maps each pipeline question (new 1–13) to the original report's label;
  - pulls the validator's headline material (raw/Q{n}_summary.json, the per-Q
    line in SUMMARY.md) and the original's matching material (the F:/A: lines of
    the `## Q{orig}.` section in INVESTIGATION_SUMMARY.md) and lays them side by
    side;
  - offers a *provisional* verdict HINT only where one labelled scalar can be
    compared within the rubric's correlation tolerance — everything else is left
    PENDING;
  - writes SCORECARD_{stage}_{model}_v{n}.md with the table, a tally template,
    a method-choice-distribution stub (robustness), and — if a prior version
    exists — a "what changed" table seeded with the prior verdicts.

It NEVER assigns a final verdict. The skill scaffolds and *suggests*; a human
confirms every verdict (the validator never grades itself, and neither does
this script). See vp-scorecard/SKILL.md, SCORECARD_GUIDE.md, REPLICATION_RUBRIC.md.

The output is operator-side and withheld (the blinding linter blocks SCORECARD_*).

Usage:
    python3 vp_scorecard.py --run RUN_FOLDER --stage STAGE --model NAME [options]

    --run    PATH      validator output folder (e.g. PANEL_VAL/robustness_GPT-5.5)
    --stage  STAGE     replication | robustness | generalization
    --model  NAME      validator model (for the header / filename)
    --license TEXT     model license (recorded in the header)
    --key    PATH      results key (default: PANEL_VAL/origin_Fable-5)
    --map    PATH      questions_map.yaml (default: alongside this script)
    --out    DIR       where to write the scorecard (default: alongside this script)
    --version N        scorecard version (default: auto = highest existing + 1)
    --prior  PATH      previous scorecard to seed the "what changed" diff
                       (default: auto-detect the highest existing version)
    --print            also echo the scorecard to stdout

Exit 0 on success; 1 on a usage/IO error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
CORR_TOL = 0.05  # rubric §3 correlation tolerance, used for the advisory hint


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_map(path: Path):
    data = yaml.safe_load(path.read_text())
    return data["questions"]


def parse_key_sections(key_dir: Path):
    """Split INVESTIGATION_SUMMARY.md into {orig_number: {D,Y,F,A, raw}}."""
    summ = key_dir / "INVESTIGATION_SUMMARY.md"
    sections = {}
    if not summ.exists():
        return sections
    text = summ.read_text()
    # split on headings like "## Q4. ..."
    parts = re.split(r"\n(?=##\s*Q\d+[.\s])", text)
    for part in parts:
        m = re.match(r"##\s*Q(\d+)", part)
        if not m:
            continue
        num = int(m.group(1))
        block = {"raw": part.strip()}
        for tag in ("D", "Y", "F", "A"):
            mm = re.search(rf"\*\*{tag}:\*\*\s*(.+?)(?=\n\*\*[DYFA]:\*\*|\Z)",
                           part, re.S)
            if mm:
                block[tag] = re.sub(r"\s+", " ", mm.group(1)).strip()
        sections[num] = block
    return sections


def find_key_files(key_dir: Path, orig: int):
    """Result .txt files whose name carries this exact orig token (q4, not q14)."""
    hits = []
    for p in sorted(key_dir.glob("q*results*.txt")):
        tokens = re.split(r"[_.]", p.name)  # q10_q12_q13_results.txt -> q10,q12,q13
        if f"q{orig}" in tokens:
            hits.append(p.name)
    return hits


NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def validator_material(run_dir: Path, n: int):
    """Headline material for pipeline question n from the validator run."""
    out = {"numbers": None, "conclusion": None, "files": [], "scalars": {}}

    # 1. raw/Q{n}_summary.json (preferred — structured)
    sj = run_dir / "raw" / f"Q{n}_summary.json"
    if sj.exists():
        try:
            d = json.loads(sj.read_text())
            out["scalars"] = {k: v for k, v in d.items() if isinstance(v, (int, float))}
            out["numbers"] = ", ".join(
                f"{k}={_fmt(v)}" for k, v in d.items() if isinstance(v, (int, float)))
            out["files"].append(f"raw/Q{n}_summary.json")
        except Exception:
            pass

    # 2. fall back to a flat Q{n}_raw.csv (e.g. the Laguna layout)
    if not out["numbers"]:
        csv = run_dir / f"Q{n}_raw.csv"
        if csv.exists():
            lines = csv.read_text().splitlines()[:3]
            out["numbers"] = " | ".join(lines)
            out["files"].append(f"Q{n}_raw.csv")

    # 3. conclusion line(s) from SUMMARY.md  (- Q2: ...  /  - Q8/Q9: ...)
    summ = run_dir / "SUMMARY.md"
    if summ.exists():
        conc = []
        for line in summ.read_text().splitlines():
            if re.match(rf"^[-*]\s*Q0*{n}\b", line) or re.match(rf"^[-*]\s*Q\d+/Q0*{n}\b", line):
                conc.append(line.lstrip("-* ").strip())
        if conc:
            out["conclusion"] = " / ".join(conc)
    return out


def _fmt(v):
    if isinstance(v, float):
        if abs(v) < 1e-3 or abs(v) >= 1e4:
            return f"{v:.2e}"
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(v)


# --------------------------------------------------------------------------- #
# Advisory verdict hint (transparent, conservative, always provisional)
# --------------------------------------------------------------------------- #
def verdict_hint(vmat, key_block):
    """Suggest only when a single comparable correlation is in tolerance.

    Returns (hint, basis) or (None, None). NEVER authoritative — the human
    confirms. We compare a validator 'pearson_r'/'r' scalar against an
    'r = X' value in the key's findings line, within the rubric tolerance.
    """
    if not vmat.get("scalars") or not key_block:
        return None, None
    vr = None
    for k, v in vmat["scalars"].items():
        if k.lower() in ("pearson_r", "r", "corr", "correlation"):
            vr = v
            break
    if vr is None:
        return None, None
    ftext = key_block.get("F", "") + " " + key_block.get("A", "")
    krs = [float(x) for x in re.findall(r"r\s*=\s*([-+]?\.?\d*\.?\d+)", ftext)]
    krs += [float(x) for x in re.findall(r"=\s*\*\*([-+]?\.?\d+)\*\*", ftext)]
    for kr in krs:
        if abs(abs(kr) - abs(vr)) <= CORR_TOL and (kr >= 0) == (vr >= 0):
            return "REPRODUCED?", f"r {vr:+.3f} vs key r {kr:+.3f} (Δ≤{CORR_TOL})"
    return None, None


# --------------------------------------------------------------------------- #
# Prior-version handling
# --------------------------------------------------------------------------- #
def existing_versions(out_dir: Path, stage: str, label: str):
    pat = re.compile(rf"SCORECARD_{re.escape(stage)}_{re.escape(label)}_v(\d+)\.md$")
    found = {}
    for p in out_dir.glob(f"SCORECARD_{stage}_{label}_v*.md"):
        m = pat.search(p.name)
        if m:
            found[int(m.group(1))] = p
    return found


VERDICT_VOCAB = ["REPRODUCED", "CONVERGED", "DIVERGED", "INCOMPLETE",
                 "GENERALIZES", "SAMPLE-SPECIFIC", "N-A", "PENDING"]


def parse_prior_verdicts(prior_path: Path):
    """Pull {q_number: verdict} from a prior scorecard's table.

    Column-based + vocabulary-driven so markdown/annotations (**bold**, ⬆, ✓,
    *(FRAGILE)*) don't break it; preserves combos like 'CONVERGED / N-A'.
    """
    verdicts = {}
    if not prior_path or not prior_path.exists():
        return verdicts
    for line in prior_path.read_text().splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3 or not cols[0].isdigit():
            continue
        vcell = cols[2].upper()
        found = [v for v in VERDICT_VOCAB if v in vcell]
        if found:
            # keep source order for combos (e.g. CONVERGED / N-A)
            found.sort(key=lambda v: vcell.index(v))
            verdicts[int(cols[0])] = " / ".join(found)
    return verdicts


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def cell(s, width=0):
    s = (s or "—").replace("\n", " ").replace("|", "\\|").strip()
    return s


def load_compare_notes(run_dir: Path, override: Path | None):
    """Per-question notes saved from the GUI Compare tab (operator-side)."""
    p = override or (HERE / "_compare_notes" / f"{run_dir.name}.json")
    if p and p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def build_scorecard(qmap, key_sections, key_dir, run_dir, stage, model, license_,
                    version, prior_verdicts, prior_name, notes=None):
    notes = notes or {}
    L = []
    title = f"Validation Scorecard — {stage} / {model} — v{version} (SKELETON)"
    L.append(f"# {title}\n")
    L.append(f"*Operator-only, withheld. **Auto-generated skeleton** by "
             f"`vp_scorecard.py` — every verdict below is PROVISIONAL and must be "
             f"confirmed by a human grader (the validator never grades itself, and "
             f"neither does this script). Graded against `{key_dir.name}/` per "
             f"`HIDDEN/REPLICATION_RUBRIC.md`; numbering is the new 1–13 with the "
             f"original label in the Note. Run: `{run_dir.name}/`. "
             f"Model license: {license_ or '(record)'}. "
             + (f"Prior: `{prior_name}`." if prior_name else "First pass.")
             + "*\n")

    L.append("## Verdict legend\n")
    L.append("- **REPRODUCED** — same method, numbers match within tolerance.")
    L.append("- **CONVERGED** — different defensible method, same conclusion (a pass).")
    L.append("- **DIVERGED** — conclusion or key number disagrees → trigger a localizing second pass.")
    L.append("- **INCOMPLETE** — intended analysis not run (method gap / data limit).")
    L.append("- **N-A** — not answerable from the data. · *FRAGILE* — original flagged it tentative (a miss is noted, not failed).")
    if stage == "generalization":
        L.append("- Stage-3 also uses **GENERALIZES / SAMPLE-SPECIFIC**.")
    L.append("")

    L.append("## Scorecard\n")
    L.append("| Q | Topic | Verdict | Method vs. orig | Validator result | Original result | Note |")
    L.append("|---|---|---|---|---|---|---|")

    rows_meta = []
    for q in qmap:
        n, orig, topic = q["n"], q["orig"], q["topic"]
        kb = key_sections.get(orig, {})
        vmat = validator_material(run_dir, n)
        hint, basis = verdict_hint(vmat, kb)

        # validator cell
        vparts = []
        if vmat["numbers"]:
            vparts.append(vmat["numbers"])
        if vmat["conclusion"]:
            vparts.append(vmat["conclusion"])
        vcell = cell(" — ".join(vparts)) if vparts else "⚠ not found — locate manually"

        # original cell: prefer the F: findings line
        ocell = cell(kb.get("F")) if kb.get("F") else cell(kb.get("raw", "")[:200])

        verdict = f"_{hint}_" if hint else "**PENDING**"
        fragile = " *(FRAGILE)*" if q.get("fragile") else ""
        note_bits = [f"orig Q{orig}"]
        if basis:
            note_bits.append(f"hint: {basis}")
        kfiles = find_key_files(key_dir, orig)
        if kfiles:
            note_bits.append("key: " + ", ".join(kfiles))
        note = cell("; ".join(note_bits)) + fragile
        qnote = notes.get(str(n))
        if qnote:
            note += " · 📝 " + cell(qnote)

        L.append(f"| {n} | {cell(topic)} | {verdict} | _(record)_ | {vcell} | {ocell} | {note} |")
        rows_meta.append((n, topic, hint))

    L.append("")
    L.append("*Verdicts in _italics with a `?`_ are advisory auto-hints (one comparable "
             "scalar within tolerance); **PENDING** = the grader must read both sides and "
             "decide. Fill the **Method vs. orig** column from the validator's "
             "`APPROACH.md` / `INVEST_METH.md`.*\n")

    # tally template
    L.append("## Tally (fill after grading)\n")
    L.append("- **Reproduced:** … · **Converged:** … · **Diverged:** … · **Incomplete:** … · **N-A:** …")
    L.append(f"- Total questions: {len(qmap)}\n")

    if stage == "robustness":
        L.append("## Method-choice distribution (compile across robustness models)\n")
        L.append("*Per question, how many independent models chose each method — a first-class "
                 "finding (method-settled vs. method-ambiguous). Fill from each run's `APPROACH.md`.*\n")
        for n, topic, _ in rows_meta:
            L.append(f"- Q{n} {topic}: …")
        L.append("")

    # second-pass column reminder
    L.append("## Second pass (for any DIVERGED row)\n")
    L.append("Re-run that question with the **original method pinned**: matches → it was a "
             "method difference (record as such); still differs → a genuine discrepancy to "
             "investigate. Add the second-pass result to the row's Note.\n")

    # what-changed diff
    if prior_verdicts:
        L.append(f"## What changed from {prior_name}\n")
        L.append("| Q | prior → now | Why it moved |")
        L.append("|---|---|---|")
        for n, topic, hint in rows_meta:
            pv = prior_verdicts.get(n, "—")
            L.append(f"| {n} | {pv} → _(fill)_ | _(fill once graded)_ |")
        L.append("")

    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a scorecard skeleton for a validator run.")
    ap.add_argument("--run", required=True)
    ap.add_argument("--stage", required=True,
                    choices=["replication", "robustness", "generalization"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--license", default=None)
    ap.add_argument("--key", default=None)
    ap.add_argument("--map", default=str(HERE / "questions_map.yaml"))
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--version", type=int, default=None)
    ap.add_argument("--prior", default=None)
    ap.add_argument("--notes", default=None,
                    help="per-question notes JSON (default: _compare_notes/{run}.json)")
    ap.add_argument("--print", dest="do_print", action="store_true")
    args = ap.parse_args(argv)

    run_dir = Path(args.run).resolve()
    if not run_dir.is_dir():
        sys.stderr.write(f"run folder not found: {run_dir}\n")
        return 1
    # key default: a sibling origin_Fable-5 of the run folder's parent
    key_dir = Path(args.key).resolve() if args.key else (run_dir.parent / "origin_Fable-5")
    if not key_dir.is_dir():
        sys.stderr.write(f"results key not found: {key_dir}\n")
        return 1
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # pick up license from a driver-written provenance file if present
    license_ = args.license
    prov = run_dir / "_provenance.json"
    if license_ is None and prov.exists():
        try:
            license_ = json.loads(prov.read_text()).get("license")
        except Exception:
            pass

    label = re.sub(r"[^A-Za-z0-9._-]+", "_", args.model).strip("_")
    versions = existing_versions(out_dir, args.stage, label)
    version = args.version or (max(versions) + 1 if versions else 1)

    prior_path = Path(args.prior).resolve() if args.prior else None
    if prior_path is None:
        lower = [v for v in versions if v < version]
        if lower:
            prior_path = versions[max(lower)]
    prior_verdicts = parse_prior_verdicts(prior_path) if prior_path else {}

    qmap = load_map(Path(args.map))
    key_sections = parse_key_sections(key_dir)
    notes = load_compare_notes(run_dir, Path(args.notes).resolve() if args.notes else None)

    md = build_scorecard(qmap, key_sections, key_dir, run_dir, args.stage,
                         args.model, license_, version, prior_verdicts,
                         prior_path.name if prior_path else None, notes)

    out_path = out_dir / f"SCORECARD_{args.stage}_{label}_v{version}.md"
    out_path.write_text(md)

    n_found = sum(1 for q in qmap if validator_material(run_dir, q["n"])["numbers"]
                  or validator_material(run_dir, q["n"])["conclusion"])
    n_hint = len(re.findall(r"\| _[A-Z]+\?_ \|", md))
    print(f"Wrote {out_path}")
    print(f"  questions: {len(qmap)} | validator material found: {n_found} | "
          f"advisory hints: {n_hint} | notes folded in: {len(notes)} | "
          f"prior: {prior_path.name if prior_path else 'none'}")
    print("  All verdicts are PROVISIONAL — confirm each by hand before this scorecard is final.")
    if args.do_print:
        print("\n" + md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
