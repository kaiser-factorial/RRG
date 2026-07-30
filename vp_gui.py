#!/usr/bin/env python3
"""
vp_gui.py — a small local web GUI for the validation pipeline.

A single-file, stdlib-only web app to handle the mechanical bookkeeping while
you talk to validators in your CLI/Hermes workflow:

  • Dashboard — a stage × model grid: packaged / returned / graded at a glance.
  • Build     — pick a stage + model, assemble the package and run the blinding
                gate (dry-run / force toggles); see PASS/FAIL + the published
                path and where to drop returned results.
  • Runs      — browse a run folder's files; view text and images in-browser.
  • Compare   — step through Q1–Q13 and see the validator's figure(s) beside the
                original's, with the scorecard's side-by-side material underneath.
  • Scorecards— generate a scorecard skeleton for a run and read it; open existing ones.

The backend only shells out to the scripts you already have (vp_driver.py,
vp_blinding_lint.py, vp_scorecard.py) and reads files under the project root —
every path is confined to the repo, and it binds to 127.0.0.1 only.

Run:
    python3 vp_gui.py            # opens http://127.0.0.1:8765 in your browser
    python3 vp_gui.py --port 9000 --no-browser
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(1)

def find_project_root(start: Path) -> Path:
    """Working project root: $RRG_PROJECT_ROOT → `.rrg_root` marker → a data dir
    (operator/shared/data, or legacy PANEL_VAL/DataAnal) → the parent."""
    import os
    env = os.environ.get("RRG_PROJECT_ROOT")
    if env:
        return Path(env).resolve()
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / ".rrg_root").exists():
            return cand
    markers = ("operator", "shared", "data", "PANEL_VAL", "DataAnal")
    for cand in [p, *p.parents]:
        if any((cand / m).is_dir() for m in markers):
            return cand
    return p.parent


HERE = Path(__file__).resolve().parent
REPO = find_project_root(HERE)              # the working project root (holds .rrg_root)
CONFIG = HERE / "vp_config.yaml"
STUDY_CONFIG = HERE / "study.yaml"          # per-lab cartridge (optional)
QMAP = HERE / "questions_map.yaml"
OPERATOR = REPO / "operator"
KEY_DIR = OPERATOR / "origin_Fable-5"
STAGES = ["replication", "robustness", "generalization"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def load_yaml(p):
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def safe_label(model: str) -> str:
    base = re.split(r"[(/]", model)[0].strip()
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_") or "model"


def confine(rel: str) -> Path | None:
    """Resolve a request path under REPO; return None if it escapes."""
    try:
        p = (REPO / rel).resolve()
        p.relative_to(REPO)
        return p
    except Exception:
        return None


def run_script(script: str, args: list[str]):
    cmd = [sys.executable, str(HERE / script)] + args
    p = subprocess.run(cmd, capture_output=True, text=True)
    data = None
    if p.stdout.strip().startswith("{"):
        try:
            data = json.loads(p.stdout)
        except Exception:
            data = None
    return {"returncode": p.returncode, "stdout": p.stdout,
            "stderr": p.stderr, "json": data}


def roster_models(cfg, stage):
    out = []
    for e in cfg.get("roster", {}).get(stage, []):
        out.append({"model": e.get("model"), "label": safe_label(e.get("model", "")),
                    "type": e.get("type"), "license": e.get("license"),
                    "vendor": e.get("vendor"), "status": e.get("status")})
    return out


def list_runs():
    runs = []
    if not OPERATOR.exists():
        return runs
    for d in sorted(OPERATOR.iterdir()):
        if not d.is_dir():
            continue
        m = re.match(r"(replication|robustness|generalization)_(.+)", d.name)
        if m or d.name == "origin_Fable-5":
            stage = m.group(1) if m else "origin(key)"
            label = m.group(2) if m else "Fable-5"
            n_files = sum(1 for _ in d.rglob("*") if _.is_file())
            runs.append({"name": d.name, "stage": stage, "label": label,
                         "n_files": n_files})
    return runs


def list_scorecards():
    cards = []
    for p in sorted(HERE.glob("SCORECARD_*.md")):
        if p.name == "SCORECARD_GUIDE.md":      # the guide, not a scorecard
            continue
        cards.append({"name": p.name, "rel": str(p.relative_to(REPO))})
    return cards


def list_prompts():
    """Prompt template .md files under the repo's prompts/ dir."""
    pdir = HERE / "prompts"
    out = []
    if pdir.is_dir():
        for p in sorted(pdir.glob("*.md")):
            out.append({"name": p.name, "rel": str(p.relative_to(REPO))})
    return out


def q_figures(run_name: str, n: int, qmap):
    """Validator figs for new Q{n} + original figs for the mapped orig Q."""
    qrec = next((q for q in qmap if q["n"] == n), None)
    orig = qrec["orig"] if qrec else n
    topic = qrec["topic"] if qrec else ""
    run_dir = OPERATOR / run_name
    # boundary so Q1 != Q11/Q12/Q13
    vpat = re.compile(rf"(?i)(^|[^0-9])Q0*{n}(?![0-9])")
    opat = re.compile(rf"(?i)^q0*{orig}(?![0-9])")

    def imgs(base, pat, match_name_only=False):
        hits = []
        if not base.exists():
            return hits
        for p in sorted(base.rglob("*")):
            if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif"):
                continue
            target = p.name if match_name_only else (p.name)
            if pat.search(target):
                hits.append(str(p.relative_to(REPO)))
        return hits

    return {"q": n, "orig": orig, "topic": topic,
            "validator": imgs(run_dir, vpat),
            "original": imgs(KEY_DIR, opat, match_name_only=True)}


NOTES_DIR = HERE / "_compare_notes"     # operator-side; never inside a run folder


def parse_prompt_turns(doc_path: Path, mode: str | None = None):
    """Split a staged prompt doc into ordered turns + operator reminders.

    Each '## Turn N — title' becomes a turn; its paste text is the fenced code
    block (turns with no block, e.g. an operator-led discussion, are marked
    paste=False). The '## Operator reminders (do not paste)' section is returned
    separately and is NEVER shown as a paste block.

    A turn heading may carry a `{mode:discuss}` / `{mode:nodiscuss}` tag. When a
    `mode` is given, turns tagged for the *other* mode are dropped; untagged
    turns always appear. The 'Turn N — ' prefix is stripped from the title (the
    UI renumbers), and the mode tag is removed from the displayed title.
    """
    turns, reminders = [], []
    if not doc_path.is_file():
        return turns, reminders
    text = doc_path.read_text()
    for part in re.split(r"\n(?=## )", text):
        m = re.match(r"## (.+)", part)
        if not m:
            continue
        head = m.group(1).strip()
        body = part[m.end():]
        # pull out an optional {mode:...} tag
        tag = re.search(r"\{mode:(\w+)\}", head)
        tmode = tag.group(1) if tag else None
        head = re.sub(r"\s*\{mode:\w+\}", "", head).strip()
        low = head.lower()
        if low.startswith("turn"):
            if mode and tmode and tmode != mode:
                continue
            title = re.sub(r"(?i)^turn\s*\d+\s*[—–-]\s*", "", head).strip()
            cb = re.search(r"```(.*?)```", body, re.S)
            turns.append({"title": title,
                          "text": cb.group(1).strip() if cb else "",
                          "paste": bool(cb), "mode": tmode})
        elif low.startswith("operator reminder"):
            reminders = [l.strip("-* ").strip() for l in body.splitlines()
                         if l.strip().startswith(("-", "*"))]
    return turns, reminders


def load_study():
    """The per-lab study cartridge (study.yaml). Empty dict if absent."""
    if STUDY_CONFIG.exists():
        return load_yaml(STUDY_CONFIG) or {}
    return {}


def _basename(p):
    return Path(p).name if p else ""


def study_modules(study):
    """Which optional cartridge modules are on (drives {#name}…{/name} blocks)."""
    s = (study or {}).get("study", {})
    return {
        "given_solution": bool((s.get("given_solution") or {}).get("enabled")),
        "aux": bool(((s.get("dataset") or {}).get("aux") or {}).get("enabled")),
        "method_guide": bool(((s.get("deliverable") or {}).get("method_guide") or {}).get("enabled")),
        "additional": bool(s.get("additional")),
    }


def study_placeholders(study, label, out_folder, report):
    """Flat {PLACEHOLDER: value} map merging cartridge + per-run values.

    File fields resolve to *basenames* (that's how prompts reference the
    attached files); prose fields pass through verbatim (they may themselves
    embed placeholders, resolved by the recursive fill in render_prompt)."""
    s = (study or {}).get("study", {})
    ds = s.get("dataset", {}) or {}
    aux = ds.get("aux", {}) or {}
    gs = s.get("given_solution", {}) or {}
    qs = s.get("questions", {}) or {}
    hc = s.get("held_constants", {}) or {}
    og = s.get("original", {}) or {}
    dl = s.get("deliverable", {}) or {}
    mg = dl.get("method_guide", {}) or {}
    fmts = ds.get("formats") or []
    add_lines = []
    for it in (s.get("additional") or []):
        it = it or {}
        nm = (it.get("name") or "").strip()
        nt = (it.get("note") or "").strip()
        fb = _basename(it.get("file"))
        line = "- " + (nm or fb or "input")
        if nt:
            line += f" — {nt}"
        if fb:
            line += f" (in {fb})"
        add_lines.append(line)
    return {
        "{MODEL}": label or "",
        "{OUTPUT_FOLDER}": out_folder or "",
        "{REPORT_NAME}": report or "",
        "{STUDY_TITLE}": s.get("title", "") or "",
        "{STUDY_OVERVIEW}": _basename(s.get("overview_file")),
        "{MAIN_DATASET}": ds.get("main_name", "") or "",
        "{MERGE_KEY}": ds.get("merge_key", "") or "",
        "{FORMATS}": " / ".join("." + f for f in fmts),
        "{CODEBOOK}": _basename(ds.get("codebook")),
        "{SUBSET_OVERVIEW}": _basename(ds.get("subset_overview")),
        "{DATA_ORIENTATION}": (ds.get("orientation") or "").strip(),
        "{AUX_DATASET}": aux.get("name", "") or "",
        "{AUX_NOTE}": (aux.get("note") or "").strip(),
        "{SOLUTION_GLOSSARY}": _basename(gs.get("glossary")),
        "{GIVEN_SOLUTION_NOTE}": (gs.get("note") or "").strip(),
        "{QUESTIONS_FILE}": _basename(qs.get("file")),
        "{N_QUESTIONS}": str(qs.get("count", "") or ""),
        "{HELD_CONSTANTS_FILE}": _basename(hc.get("file")),
        "{HELD_CONSTANTS_SUMMARY}": (hc.get("summary") or "").strip(),
        "{HELD_CONSTANT_GROUPS}": (hc.get("qa_groups") or "").strip(),
        "{ORIGINAL_PROTOCOL}": _basename(og.get("methodology_file")),
        "{RESULTS_KEY}": _basename((og.get("results_key") or "").rstrip("/")),
        "{REPORTING_SPEC}": (dl.get("reporting_spec") or "").strip(),
        "{METHOD_GUIDE_NAME}": mg.get("name", "") if mg.get("enabled") else "",
        "{METHOD_GUIDE_FILE}": _basename(mg.get("file")) if mg.get("enabled") else "",
        "{ADDITIONAL}": "\n".join(add_lines),
    }


def render_prompt(text, ph, mods):
    """Fill a template: drop disabled {#module}…{/module} blocks, then substitute
    placeholders. Repeats so placeholders nested inside injected prose resolve."""
    if not text:
        return text

    def drop(m):
        return m.group(2) if mods.get(m.group(1)) else ""

    for _ in range(4):
        before = text
        text = re.sub(r"\{#(\w+)\}(.*?)\{/\1\}", drop, text, flags=re.S)
        for k, v in ph.items():
            text = text.replace(k, v)
        if text == before:
            break
    # tidy a couple of spacing artifacts left by dropped inline blocks
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text


def fill_turns(turns, reminders, ph, mods):
    turns = [{"title": render_prompt(t["title"], ph, mods),
              "text": render_prompt(t["text"], ph, mods),
              "paste": t["paste"]} for t in turns]
    reminders = [render_prompt(r, ph, mods) for r in reminders]
    return turns, reminders


def render_stage_prompt(cfg, study, stage, label, mode):
    """Fill a stage's prompt_doc with the cartridge for a given model label."""
    scfg = next((s for s in cfg.get("stages", []) if s.get("id") == stage), {})
    doc = scfg.get("prompt_doc")
    turns, reminders = parse_prompt_turns(REPO / doc, mode) if doc else ([], [])
    out_folder = scfg.get("output_folder", "{MODEL}/").replace("{MODEL}", label)
    report = scfg.get("report_name", "{MODEL}_Report.docx").replace("{MODEL}", label)
    ph = study_placeholders(study, label, out_folder, report)
    turns, reminders = fill_turns(turns, reminders, ph, study_modules(study))
    return {"stage": stage, "doc": doc, "output_folder": out_folder.rstrip("/"),
            "report_name": report, "turns": turns, "reminders": reminders}


def preflight(cfg):
    """Cartridge readiness: do referenced files exist, and do the wired stage
    prompts fill with no leftover placeholders?"""
    study = load_study()
    s = (study or {}).get("study", {})
    ds = s.get("dataset", {}) or {}
    gs = s.get("given_solution", {}) or {}
    qs = s.get("questions", {}) or {}
    hc = s.get("held_constants", {}) or {}
    og = s.get("original", {}) or {}
    dl = s.get("deliverable", {}) or {}
    mg = dl.get("method_guide", {}) or {}
    checks = []

    def fc(label, path, needed=True):
        if not path:
            checks.append({"label": label, "path": "", "ok": not needed,
                           "detail": "not set" if needed else "not set (ok)"})
            return
        p = confine(path)
        ok = p is not None and p.exists()
        checks.append({"label": label, "path": path, "ok": ok,
                       "detail": "found" if ok else "MISSING or outside repo"})

    fc("study overview", s.get("overview_file"))
    fc("dataset source", ds.get("source"))
    fc("codebook", ds.get("codebook"))
    fc("subset overview", ds.get("subset_overview"), needed=False)
    if gs.get("enabled"):
        fc("given-solution glossary", gs.get("glossary"))
        for a in (gs.get("artifacts") or []):
            fc("given-solution artifact", a)
    fc("questions file", qs.get("file"))
    fc("questions map", qs.get("map"), needed=False)
    fc("held-constants file", hc.get("file"))
    fc("original methodology", og.get("methodology_file"))
    fc("results key", og.get("results_key"))
    if mg.get("enabled"):
        fc("method-guide file", mg.get("file"))
    for it in (s.get("additional") or []):
        it = it or {}
        fc("additional: " + (it.get("name") or "input"), it.get("file"))

    renders = []
    for stage in STAGES:
        scfg = next((x for x in cfg.get("stages", []) if x.get("id") == stage), {})
        if not scfg.get("prompt_doc"):
            renders.append({"stage": stage, "ok": None, "detail": "no prompt wired"})
            continue
        r = render_stage_prompt(cfg, study, stage, "SampleModel", "discuss")
        txt = " ".join(t["title"] + " " + t["text"] for t in r["turns"]) + " " + " ".join(r["reminders"])
        leftover = sorted(set(re.findall(r"\{[A-Z_]{2,}\}", txt)))
        renders.append({"stage": stage, "ok": not leftover,
                        "detail": "fills clean" if not leftover else "unfilled: " + ", ".join(leftover)})

    ok = all(c["ok"] for c in checks) and all(r["ok"] is not False for r in renders)
    return {"ok": ok, "checks": checks, "renders": renders}


def render_dispatch(cfg, prov, stage, mode: str | None = None):
    """Structured, multi-turn hand-off for a freshly published package.

    No prompt is baked into a command (the interaction is multi-turn). We return
    the working dir (the empty output folder), the start command, and the stage
    prompt's turns to paste in order. The package path is shown for attaching.
    """
    if not prov:
        return None
    d = cfg.get("dispatch", {})
    model = prov.get("model", "")
    slug = d.get("openrouter", {}).get(model, model)
    start = d.get("start_template", "hermes run --model {openrouter}").format(
        openrouter=slug, model=model)
    scfg = next((s for s in cfg.get("stages", []) if s.get("id") == stage), {})
    doc = scfg.get("prompt_doc")
    turns, reminders = parse_prompt_turns(REPO / doc, mode) if doc else ([], [])
    # fill cartridge placeholders + drop disabled modules
    study = load_study()
    label = prov.get("label", "")
    out_fold = scfg.get("output_folder", "{MODEL}/").replace("{MODEL}", label)
    report = scfg.get("report_name", "{MODEL}_Report.docx").replace("{MODEL}", label)
    ph = study_placeholders(study, label, out_fold, report)
    turns, reminders = fill_turns(turns, reminders, ph, study_modules(study))
    output = prov.get("output_folder", "")
    return {
        "slug": slug, "package": prov.get("package_dir", ""), "output": output,
        "cd_cmd": f"cd {output}", "start_cmd": start,
        "turns": turns, "reminders": reminders,
        "n_turns": len(turns),
    }


def notes_path(run: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", run)
    return NOTES_DIR / f"{safe}.json"


def load_notes(run: str) -> dict:
    p = notes_path(run)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def save_note(run: str, q, text: str):
    NOTES_DIR.mkdir(exist_ok=True)
    notes = load_notes(run)
    notes[str(q)] = text
    notes_path(run).write_text(json.dumps(notes, indent=2))
    return notes


def read_provenance_log():
    """Every published-package record, newest first, with repo-relative paths."""
    log = OPERATOR / "_packages" / "provenance_log.jsonl"
    out = []
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            def rel(p):
                try:
                    return str(Path(p).resolve().relative_to(REPO))
                except Exception:
                    return p
            out.append({
                "stage": d.get("stage"), "label": d.get("label"),
                "model": d.get("model"), "timestamp": d.get("timestamp"),
                "package_dir": rel(d.get("package_dir", "")),
                "output_folder": rel(d.get("output_folder", "")),
                "lint": d.get("blinding_lint_result"),
                "forced": d.get("forced_override"),
            })
    out.reverse()
    return out


def dashboard(cfg):
    log = OPERATOR / "_packages" / "provenance_log.jsonl"
    packaged = set()
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                d = json.loads(line)
                packaged.add((d["stage"], d["label"]))
            except Exception:
                pass
    grid = []
    for stage in STAGES:
        for m in roster_models(cfg, stage):
            label = m["label"]
            pkg_dir = OPERATOR / "_packages" / stage / label
            run_dir = OPERATOR / f"{stage}_{label}"
            returned = run_dir.is_dir() and any(run_dir.rglob("*"))
            graded = any(HERE.glob(f"SCORECARD_{stage}_{label}_v*.md"))
            grid.append({
                "stage": stage, "model": m["model"], "label": label,
                "type": m["type"], "license": m["license"], "note": m["status"],
                "packaged": (stage, label) in packaged or pkg_dir.exists(),
                "returned": bool(returned),
                "graded": bool(graded),
            })
    return grid


# --------------------------------------------------------------------------- #
# HTTP handler
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- GET ----
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        cfg = load_yaml(CONFIG)
        qmap = load_yaml(QMAP).get("questions", [])

        if u.path == "/":
            return self._send(200, HTML, "text/html; charset=utf-8")

        if u.path == "/api/config":
            origin = cfg.get("origin", {}) or {}
            src = origin.get("source_data")
            return self._send(200, {
                "stages": STAGES,
                "roster": {s: roster_models(cfg, s) for s in STAGES},
                "questions": qmap,
                "repo": str(REPO),
                "source_data": src,
                "source_exists": bool(src and (REPO / src).exists()),
                "prompt_docs": {s.get("id"): s.get("prompt_doc")
                                for s in cfg.get("stages", []) if s.get("id")},
            })

        if u.path == "/api/built":
            return self._send(200, {"built": read_provenance_log()})

        if u.path == "/api/runs":
            return self._send(200, {"runs": list_runs(),
                                    "scorecards": list_scorecards(),
                                    "prompts": list_prompts()})

        if u.path == "/api/prompt":
            name = (q.get("run") or [""])[0]
            run = next((r for r in list_runs() if r["name"] == name), None)
            if not run:
                return self._send(404, {"error": "run not found"})
            stage, label = run["stage"], run["label"]
            mode = (q.get("mode") or ["discuss"])[0]
            res = render_stage_prompt(cfg, load_study(), stage, label, mode)
            res.update({"run": name, "label": label})
            return self._send(200, res)

        if u.path == "/api/study":
            return self._send(200, {"study": load_study(),
                                    "exists": STUDY_CONFIG.exists()})

        if u.path == "/api/preflight":
            return self._send(200, preflight(cfg))

        if u.path == "/api/study_preview":
            stage = (q.get("stage") or ["robustness"])[0]
            mode = (q.get("mode") or ["discuss"])[0]
            label = (q.get("label") or ["SampleModel"])[0]
            return self._send(200, render_stage_prompt(cfg, load_study(),
                                                       stage, label, mode))

        if u.path == "/api/dashboard":
            return self._send(200, {"grid": dashboard(cfg)})

        if u.path == "/api/tree":
            name = (q.get("run") or [""])[0]
            base = OPERATOR / name
            if not base.is_dir() or confine(f"operator/{name}") is None:
                return self._send(404, {"error": "run not found"})
            files = sorted(str(p.relative_to(REPO)) for p in base.rglob("*") if p.is_file())
            return self._send(200, {"files": files})

        if u.path == "/api/figures":
            name = (q.get("run") or [""])[0]
            n = int((q.get("q") or ["1"])[0])
            return self._send(200, q_figures(name, n, qmap))

        if u.path == "/api/notes":
            name = (q.get("run") or [""])[0]
            return self._send(200, {"notes": load_notes(name)})

        if u.path in ("/api/file", "/api/scorecard"):
            rel = (q.get("path") or [""])[0]
            p = confine(rel)
            if p is None or not p.is_file():
                return self._send(404, {"error": "not found"})
            try:
                return self._send(200, {"path": rel, "text": p.read_text(errors="replace")})
            except Exception as e:
                return self._send(500, {"error": str(e)})

        if u.path == "/api/image":
            rel = (q.get("path") or [""])[0]
            p = confine(rel)
            if p is None or not p.is_file():
                return self._send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            return self._send(200, p.read_bytes(), ctype)

        return self._send(404, {"error": "unknown endpoint"})

    # ---- POST ----
    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")

        if u.path == "/api/build":
            stage = payload.get("stage")
            model = payload.get("model")
            args = ["--stage", stage, "--model", model, "--json"]
            if payload.get("dry_run"):
                args.append("--dry-run")
            if payload.get("force"):
                args.append("--force")
            res = run_script("vp_driver.py", args)
            j = res.get("json") or {}
            # a dispatch hand-off only makes sense for a real, published package
            if not payload.get("dry_run") and not j.get("blocked"):
                res["dispatch"] = render_dispatch(load_yaml(CONFIG),
                                                  j.get("provenance"), stage,
                                                  payload.get("mode"))
            return self._send(200, res)

        if u.path == "/api/notes":
            return self._send(200, {"notes": save_note(payload.get("run", ""),
                                                        payload.get("q"),
                                                        payload.get("text", ""))})

        if u.path == "/api/study":
            data = payload.get("study")
            if not isinstance(data, dict):
                return self._send(400, {"error": "missing study object"})
            header = ("# study cartridge (saved from the Setup tab)\n"
                      "# See study.example.yaml for field annotations and "
                      "docs/GENERALIZATION_DESIGN.md.\n")
            try:
                body = yaml.safe_dump({"study": data}, sort_keys=False,
                                      allow_unicode=True, width=100)
                STUDY_CONFIG.write_text(header + body)
            except Exception as e:
                return self._send(500, {"error": f"save failed: {e}"})
            return self._send(200, {"ok": True, "saved": str(STUDY_CONFIG.name)})

        if u.path == "/api/convert":
            src = payload.get("source")
            p = confine(src) if src else None
            if p is None or not p.is_file():
                return self._send(400, {"error": "source not found / outside repo"})
            args = [str(p), "--json", "--formats"] + (payload.get("formats") or ["csv"])
            if payload.get("labeled"):
                args.append("--labeled")
            if payload.get("out"):
                op = confine(payload["out"])
                if op is not None:
                    args += ["--out", str(op)]
            return self._send(200, run_script("convert_data.py", args))

        if u.path == "/api/make_scorecard":
            args = ["--run", str(OPERATOR / payload["run"]),
                    "--stage", payload["stage"], "--model", payload["model"]]
            if payload.get("license"):
                args += ["--license", payload["license"]]
            res = run_script("vp_scorecard.py", args)
            # surface the written path
            m = re.search(r"Wrote (.+)", res["stdout"])
            if m:
                wp = Path(m.group(1).strip())
                try:
                    res["rel"] = str(wp.resolve().relative_to(REPO))
                except Exception:
                    res["rel"] = None
            return self._send(200, res)

        return self._send(404, {"error": "unknown endpoint"})


# --------------------------------------------------------------------------- #
# Front-end (single embedded page; no external assets)
# --------------------------------------------------------------------------- #
HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Validation Pipeline</title>
<style>
:root{--bg:#0f1115;--panel:#181b22;--panel2:#1f232c;--line:#2a2f3a;--fg:#e6e9ef;--mut:#9aa3b2;--acc:#6ea8fe;--ok:#3fb950;--bad:#f85149;--warn:#d29922;}
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
button,a,.chk,select,input,summary,tr{transition:background .15s ease,color .15s ease,border-color .15s ease,filter .15s ease,transform .08s ease}
button:active{transform:translateY(1px)}
header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:18px;background:var(--panel)}
header h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.3px}
nav{display:flex;gap:4px}
nav button{background:none;border:1px solid transparent;color:var(--mut);padding:6px 12px;border-radius:7px;cursor:pointer;font-size:13px}
nav button:hover{color:var(--fg);background:var(--panel2)}
nav button.active{color:var(--fg);background:var(--panel2);border-color:var(--line)}
main{padding:20px;max-width:1200px;margin:0 auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}
h2{font-size:14px;margin:0 0 12px;font-weight:600}
label{display:block;color:var(--mut);font-size:12px;margin:8px 0 3px}
select,input[type=text]{width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--fg);padding:7px 9px;border-radius:7px}
button.go{background:var(--acc);color:#06122b;border:none;padding:8px 16px;border-radius:7px;font-weight:600;cursor:pointer;margin-top:12px}
button.go:hover{filter:brightness(1.08)}
button.ghost{background:var(--panel2);border:1px solid var(--line);color:var(--fg);padding:6px 12px;border-radius:7px;cursor:pointer}
button.ghost:hover{background:var(--line);border-color:var(--acc);color:var(--fg)}
.row{display:flex;gap:14px;flex-wrap:wrap}
.row>div{flex:1;min-width:180px}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);margin-right:16px;margin-top:10px;cursor:pointer}
.chk:hover{color:var(--fg)}
.chk input{width:auto;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:500}
.pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}
.yes{background:rgba(63,185,80,.15);color:var(--ok)}
.no{background:rgba(139,148,158,.12);color:var(--mut)}
.tag.s1,.pill.yes.s1{background:rgba(63,185,80,.14);color:#3fb950;border-color:rgba(63,185,80,.4)}
.tag.s2,.pill.yes.s2{background:rgba(110,168,254,.14);color:#6ea8fe;border-color:rgba(110,168,254,.4)}
.tag.s3,.pill.yes.s3{background:rgba(163,113,247,.16);color:#a371f7;border-color:rgba(163,113,247,.4)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%}
.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}.dot.warn{background:var(--warn)}
pre{background:#0b0d11;border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;font-size:12.5px;max-height:480px}
.mut{color:var(--mut)}
.tag{font-size:11px;padding:1px 7px;border-radius:5px;background:var(--panel2);border:1px solid var(--line);color:var(--mut)}
.split{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.split h3{font-size:12px;color:var(--mut);margin:0 0 8px;text-transform:uppercase;letter-spacing:.5px}
.fig{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff;margin-bottom:10px}
.filelist{max-height:480px;overflow:auto}
.filelist a{display:block;padding:4px 8px;color:var(--acc);text-decoration:none;border-radius:6px;font-size:12.5px;cursor:pointer}
.filelist a:hover{background:var(--panel2)}
a[onclick]{cursor:pointer}
td a{color:var(--acc);text-decoration:none}
td a:hover{text-decoration:underline;filter:brightness(1.12)}
tbody tr:hover td a{filter:brightness(1.12)}
summary{cursor:pointer}
summary:hover{color:var(--fg)}
.qnav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.qnav button{width:34px;height:34px;border-radius:7px;border:1px solid var(--line);background:var(--panel2);color:var(--fg);cursor:pointer}
.qnav button:hover{border-color:var(--acc);background:var(--panel)}
.qnav button.active{background:var(--acc);color:#06122b;border-color:var(--acc);font-weight:700}
.qnav button.active:hover{filter:brightness(1.08)}
.banner{padding:10px 14px;border-radius:8px;margin-bottom:12px;font-weight:600}
.banner.ok{background:rgba(63,185,80,.13);color:var(--ok);border:1px solid rgba(63,185,80,.3)}
.banner.bad{background:rgba(248,81,73,.13);color:var(--bad);border:1px solid rgba(248,81,73,.3)}
.banner.warn{background:rgba(210,153,34,.13);color:var(--warn);border:1px solid rgba(210,153,34,.3)}
.savebox{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0;font-size:13px;word-break:break-all}
.savebox code{color:var(--acc)}
.stagechip{display:inline-flex;align-items:center;gap:7px;font-weight:600;font-size:12.5px;padding:4px 11px 4px 5px;border-radius:20px;background:var(--panel2);color:var(--fg);border:1px solid var(--line)}
.stagechip .num{display:inline-flex;width:19px;height:19px;border-radius:50%;align-items:center;justify-content:center;font-size:11px;font-weight:700;background:var(--mut);color:#06122b}
.stagechip.s1{background:rgba(63,185,80,.14);color:#3fb950;border-color:rgba(63,185,80,.4)}
.stagechip.s1 .num{background:#3fb950;color:#06210d}
.stagechip.s2{background:rgba(110,168,254,.14);color:#6ea8fe;border-color:rgba(110,168,254,.4)}
.stagechip.s2 .num{background:#6ea8fe;color:#06122b}
.stagechip.s3{background:rgba(163,113,247,.16);color:#a371f7;border-color:rgba(163,113,247,.4)}
.stagechip.s3 .num{background:#a371f7;color:#1a0b2e}
.substep{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
tr.runrow{cursor:pointer}
tr.runrow:hover{background:var(--panel2)}
tr.runrow.active{background:var(--panel2)}
tr.runrow.active td:first-child{box-shadow:inset 3px 0 0 var(--acc)}
tr.runrow.active td:first-child a{color:var(--fg);font-weight:600}
details.chunk{border:1px solid var(--line);border-radius:8px;padding:8px 11px;margin:8px 0;background:var(--bg)}
details.chunk>summary{cursor:pointer;font-size:13px}
details.chunk>summary .substep{margin-right:6px}
.empty{color:var(--mut);font-style:italic;padding:20px;text-align:center}
/* ---- motion & feedback ---- */
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes slideIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes figIn{to{opacity:1}}
#app.fade-in{animation:fadeUp .22s ease}
.banner{animation:slideIn .25s ease}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--acc);border-radius:50%;animation:spin .6s linear infinite;vertical-align:-2px}
.loading{display:flex;align-items:center;gap:9px;color:var(--mut);padding:6px 0}
button:disabled{opacity:.6;cursor:not-allowed}
button.go .spinner{border-color:rgba(6,18,43,.3);border-top-color:#06122b;margin-right:8px}
button.ghost .spinner{margin-right:7px}
select:focus,input[type=text]:focus,textarea:focus{outline:none;border-color:var(--acc);box-shadow:0 0 0 2px rgba(110,168,254,.25)}
.fig{opacity:0;transition:opacity .3s ease}
@media (prefers-reduced-motion: reduce){
  *{animation:none!important;transition-duration:.001ms!important}
  .fig{opacity:1!important}
}
</style></head>
<body>
<header>
  <h1>🔬 Validation Pipeline</h1>
  <nav id=nav>
    <button data-v=dashboard class=active>Dashboard</button>
    <button data-v=convert>Convert data</button>
    <button data-v=build>Build</button>
    <button data-v=runs>Runs</button>
    <button data-v=compare>Compare</button>
    <button data-v=scorecards>Scorecards</button>
    <button data-v=setup>Setup</button>
  </nav>
  <span class=mut id=repo style="margin-left:auto;font-size:12px"></span>
</header>
<main id=app></main>

<script>
let CFG=null, RUNS=null;
const $=(h)=>{const d=document.createElement('div');d.innerHTML=h;return d.firstElementChild;};
const api=(p)=>fetch(p).then(r=>r.json());
const post=(p,b)=>fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json());
const esc=(s)=>(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const escA=(s)=>esc(s).replace(/"/g,'&quot;');
function copyText(t,btn){navigator.clipboard.writeText(t).then(()=>{const o=btn.textContent;btn.textContent='Copied ✓';setTimeout(()=>btn.textContent=o,1200);});}
const loading=(t)=>`<div class=loading><span class=spinner></span>${t}</div>`;
async function busy(btn,label,fn){
  if(!btn)return fn();
  const o=btn.innerHTML; btn.disabled=true;
  btn.innerHTML='<span class=spinner></span>'+label;
  try{return await fn();}finally{btn.disabled=false;btn.innerHTML=o;}
}

async function boot(){
  CFG=await api('/api/config');
  document.getElementById('repo').textContent=CFG.repo;
  document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>{
    document.querySelectorAll('#nav button').forEach(x=>x.classList.remove('active'));
    b.classList.add('active'); show(b.dataset.v);
  });
  show('dashboard');
}
function show(v){const f={dashboard:viewDash,convert:viewConvert,build:viewBuild,runs:viewRuns,compare:viewCompare,scorecards:viewScore,setup:viewSetup}[v];
  const app=document.getElementById('app'); app.classList.remove('fade-in'); void app.offsetWidth; app.classList.add('fade-in'); f();}

// ---------- Convert data ----------
function viewConvert(){
  const app=document.getElementById('app');
  const src=CFG.source_data||'';
  app.innerHTML=`<div class=card><h2>Convert source data → analysis-ready derivatives</h2>
    <p class=mut style="font-size:12px">The original stays the single source of truth; derivatives are reproducible from it and verified identical after writing.</p>
    <label>Source file (repo-relative)</label>
    <input type=text id=csrc value="${esc(src)}" placeholder="DataAnal/fullSet/....sav">
    ${CFG.source_exists?'<span class="pill yes" style="margin-top:6px">source found ✓</span>':'<span class="pill no" style="margin-top:6px">not found — check path</span>'}
    <label style="margin-top:10px">Formats</label>
    <label class=chk><input type=checkbox id=cfcsv checked> csv <span class=mut>(human-readable, for exploring)</span></label>
    <label class=chk><input type=checkbox id=cfpq checked> parquet <span class=mut>(typed, for analysis)</span></label>
    <label class=chk style="margin-top:10px"><input type=checkbox id=clab> apply value labels <span class=mut>(1 → "Monogamy"; default = coded codes)</span></label>
    <div><button class=go id=cgo>Convert &amp; verify</button></div>
    <div id=cout style="margin-top:14px"></div></div>`;
  document.getElementById('cgo').onclick=async()=>{
    const fmts=[]; if(document.getElementById('cfcsv').checked)fmts.push('csv'); if(document.getElementById('cfpq').checked)fmts.push('parquet');
    const out=document.getElementById('cout');
    if(!fmts.length){out.innerHTML='<div class="banner bad">Pick at least one format.</div>';return;}
    await busy(document.getElementById('cgo'),'Converting…',async()=>{
    out.innerHTML=loading('Converting + verifying…');
    const r=await post('/api/convert',{source:document.getElementById('csrc').value,formats:fmts,labeled:document.getElementById('clab').checked});
    if(r.error){out.innerHTML='<div class="banner bad">'+esc(r.error)+'</div>';return;}
    const j=r.json;
    if(!j){out.innerHTML='<div class="banner bad">Convert failed</div><pre>'+esc(r.stderr||r.stdout)+'</pre>';return;}
    let rows=(j.outputs||[]).map(o=>{const v=o.verify||{};
      const ok=v.ok; const how=v.exact?'bit-for-bit':('to float precision (max diff '+(v.max_numeric_diff||0).toExponential(1)+')');
      return `<tr><td><b>${o.format}</b></td><td class=mut>${esc(o.name)}</td>
        <td>${ok?'<span class="pill yes">identical ✓</span>':'<span class="pill no">MISMATCH</span>'}</td>
        <td class=mut style="font-size:12px">${ok?how+'; strings exact; NaN pattern matches':esc(JSON.stringify(v))}</td></tr>`;}).join('');
    const allok=j.all_verified;
    out.innerHTML=`<div class="banner ${allok?'ok':'bad'}">${allok?'✓ All derivatives verified identical to the original':'⚠ A derivative did not verify — see below'}</div>
      <table><thead><tr><th>Format</th><th>File</th><th>Verify</th><th>Detail</th></tr></thead><tbody>${rows}</tbody></table>
      <p class=mut style="margin-top:10px">${j.n_rows} rows × ${j.n_cols} cols · mode: ${j.mode} · source sha256 <code>${esc((j.source_sha256||'').slice(0,16))}…</code> (provenance anchor). Sidecar: <code>${esc(j.sidecar)}</code> · codebook: <code>${esc(j.codebook)}</code></p>`;
    });
  };
}

// ---------- Dashboard ----------
async function viewDash(){
  const app=document.getElementById('app'); app.innerHTML='<div class=card>'+loading('Loading run status…')+'</div>';
  const {grid}=await api('/api/dashboard');
  const badge=(b,s)=>b?`<span class="pill yes ${s}">✓</span>`:'<span class="pill no">·</span>';
  let rows=grid.map(g=>{const s='s'+(STAGE_NUM[g.stage]||'');return `<tr>
    <td><span class="tag ${s}">${esc(g.stage)}</span></td>
    <td>${esc(g.model)} <span class=mut style="font-size:11px">${g.type||''}</span></td>
    <td>${badge(g.packaged,s)}</td><td>${badge(g.returned,s)}</td><td>${badge(g.graded,s)}</td>
    <td class=mut style="font-size:11px">${esc(g.note||'')}</td></tr>`;}).join('');
  app.innerHTML=`<div class=card><h2>Run status — stage × model</h2>
    <table><thead><tr><th>Stage</th><th>Model</th><th>Packaged</th><th>Returned</th><th>Graded</th><th>Note</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <p class=mut style="margin-top:10px">Packaged = a blinding-passed package was built · Returned = results are in the run folder · Graded = a scorecard exists.</p></div>`;
}

// ---------- Build ----------
let BUILT=[];
const relpath=(p)=>{if(!p)return '';const i=p.indexOf('/operator/');return i>=0?p.slice(i+1):p;};
const STAGE_NUM={replication:1,robustness:2,generalization:3};
const stageChip=(s)=>{const n=STAGE_NUM[s];return `<span class="stagechip${n?' s'+n:''}"><span class=num>${n||'•'}</span>Stage ${n||''} · ${esc(s)}</span>`;};
let BUILD_OUT={};    // 'stage||model' -> last result HTML (kept across nav)
let BUILD_SEL=null;  // {stage,model} last viewed
const bkey=(s,m)=>s+'||'+m;
const curSel=()=>({stage:document.getElementById('bstage').value, model:document.getElementById('bmodel').value});
function restoreBuildOut(){const out=document.getElementById('bout');if(!out)return;const c=curSel();out.innerHTML=BUILD_OUT[bkey(c.stage,c.model)]||'';}
async function viewBuild(){
  const app=document.getElementById('app');
  const stageOpts=CFG.stages.map(s=>`<option>${s}</option>`).join('');
  app.innerHTML=`<div class=card><h2>Build &amp; blinding-gate a package</h2>
    <div class=row>
      <div><label>Stage</label><select id=bstage>${stageOpts}</select></div>
      <div><label>Model</label><select id=bmodel></select></div>
    </div>
    <div id=bstatus style="margin-top:10px"></div>
    <label class=chk><input type=checkbox id=bdry checked> dry-run (validate, publish nothing)</label>
    <label class=chk><input type=checkbox id=bforce> force (override a HARD FAIL — logged)</label>
    <label class=chk><input type=checkbox id=bdisc checked> include methodology discussion <span class=mut>(off = model self-proposes, operator-reviewed lock)</span></label>
    <div><button class=go id=bgo>Build package</button></div>
    <div id=bout style="margin-top:14px"></div></div>`;
  const bstage=document.getElementById('bstage'), bmodel=document.getElementById('bmodel');
  if(BUILD_SEL) bstage.value=BUILD_SEL.stage;
  const fill=()=>{const s=bstage.value;
    bmodel.innerHTML=CFG.roster[s].map(m=>`<option value="${esc(m.model)}" data-label="${esc(m.label||'')}">${esc(m.model)} — ${m.type}/${esc(m.license||'')}</option>`).join('');
    if(BUILD_SEL && BUILD_SEL.stage===s) bmodel.value=BUILD_SEL.model;
    BUILD_SEL=curSel(); refreshBuildStatus(); restoreBuildOut();};
  bstage.onchange=fill;
  bmodel.onchange=()=>{BUILD_SEL=curSel(); refreshBuildStatus(); restoreBuildOut();};
  try{BUILT=(await api('/api/built')).built||[];}catch(e){BUILT=[];}
  fill();
  document.getElementById('bgo').onclick=async()=>{
   await busy(document.getElementById('bgo'),'Building…',async()=>{
    const dry=document.getElementById('bdry').checked;
    const sel=curSel();
    const out=document.getElementById('bout'); out.innerHTML=loading('Building package…');
    const r=await post('/api/build',{stage:sel.stage, model:sel.model,
      dry_run:dry, force:document.getElementById('bforce').checked,
      mode:document.getElementById('bdisc').checked?'discuss':'nodiscuss'});
    const j=r.json||{}; const okrun=r.returncode===0 && !j.blocked;
    const banner=j.blocked?'<div class="banner bad">⛔ BLOCKED by blinding gate — nothing published</div>'
      :(r.returncode===0?'<div class="banner ok">✓ '+(j.lint==='pass'?'Blinding PASS':'Forced override')+(dry?' — validated (dry-run)':' — published')+'</div>'
      :'<div class="banner bad">Error (exit '+r.returncode+')</div>');
    let saved='';
    if(okrun && dry){
      saved='<div class="banner warn">Dry-run: nothing was saved to disk. Uncheck “dry-run” and build again to publish the package.</div>';
    } else if(okrun){
      const p=j.provenance||{};
      saved=`<div class=savebox><div><span class=mut>Package saved to</span><br><code>${esc(relpath(p.package_dir))}</code></div>
        <div style="margin-top:6px"><span class=mut>Drop the validator’s returned results in</span><br><code>${esc(relpath(p.output_folder))}</code></div></div>`;
    }
    let disp='';
    if(r.dispatch){r.dispatch.stage=sel.stage; disp=renderDispatch(r.dispatch);}
    out.innerHTML=banner+saved+'<pre>'+esc((j.log||[]).join('\n')||r.stdout||r.stderr)+'</pre>'+disp;
    BUILD_OUT[bkey(sel.stage,sel.model)]=out.innerHTML; BUILD_SEL=sel;
    if(okrun && !dry){try{BUILT=(await api('/api/built')).built||[];}catch(e){} refreshBuildStatus();}
   });
  };
}
function refreshBuildStatus(){
  const el=document.getElementById('bstatus'); if(!el)return;
  const stage=document.getElementById('bstage').value;
  const sel=document.getElementById('bmodel').selectedOptions[0];
  const label=sel?sel.dataset.label:'';
  const doc=(CFG.prompt_docs||{})[stage];
  const chip=`<div style="margin-bottom:8px">${stageChip(stage)}</div>`;
  const docLine=doc
    ?`<div class=mut style="font-size:12px;margin-top:6px">Prompt template for this stage: <code>${esc(doc)}</code></div>`
    :`<div class=mut style="font-size:12px;margin-top:6px">No prompt template wired for this stage yet.</div>`;
  const hits=BUILT.filter(b=>b.stage===stage && b.label===label);
  if(hits.length){
    const last=hits[0];
    const when=last.timestamp?new Date(last.timestamp).toLocaleString():'';
    el.innerHTML=chip+`<div class="banner ok" style="margin-bottom:6px">✓ Already published${when?' — '+esc(when):''}</div>
      <div class=savebox><div><span class=mut>Package</span> <code>${esc(last.package_dir)}</code></div>
      <div style="margin-top:4px"><span class=mut>Returned-results folder</span> <code>${esc(last.output_folder)}</code></div>
      ${hits.length>1?`<div class=mut style="font-size:12px;margin-top:4px">${hits.length} builds on record — newest shown. Rebuilding writes a timestamped copy; it never overwrites.</div>`:''}</div>${docLine}`;
  } else {
    el.innerHTML=chip+`<div class=mut style="font-size:12.5px">Not built yet for this stage + model.</div>${docLine}`;
  }
}
function cmdBlock(id,text){return `<pre id=${id} style="margin:4px 0">${esc(text)}</pre>`+
  `<button class=ghost onclick="copyText(document.getElementById('${id}').textContent,this)">Copy</button>`;}
function renderDispatch(d){
  let turns=(d.turns||[]).map((t,i)=>{
    const tag=`<span class=substep>Turn ${i+1}</span>`;
    if(t.paste) return `<div style="margin:10px 0">${tag} <span class=mut style="font-size:12px">${esc(t.title)}</span>${cmdBlock('turn'+i,t.text)}</div>`;
    return `<div style="margin:10px 0">${tag} <span class=mut style="font-size:12px">${esc(t.title)}</span><p class=empty style="text-align:left;padding:6px 0">↳ operator-led — no fixed text to paste.</p></div>`;
  }).join('');
  let rem=(d.reminders||[]).length?`<details style="margin-top:10px"><summary class=mut>Operator reminders (do not paste — ${d.reminders.length})</summary><ul class=mut style="font-size:12px">${d.reminders.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul></details>`:'';
  return `<div class=card style="margin-top:12px;background:var(--panel2)">
    ${d.stage?`<div style="margin-bottom:8px">${stageChip(d.stage)} <span class=mut style="font-size:12px">— sub-steps below</span></div>`:''}
    <h2>Dispatch — hand the package to your agent CLI</h2>
    <p class=mut style="font-size:12px">Multi-turn: start the agent in the run folder, attach the package, then paste each turn in order, waiting for the model between turns.</p>
    <ol style="padding-left:18px">
      <li><b>cd into the (empty) run folder</b>${cmdBlock('dcd',d.cd_cmd)}</li>
      <li style="margin-top:8px"><b>start the agent</b> &nbsp;<span class=tag>slug: ${esc(d.slug)}</span> <span class=mut style="font-size:11px">(verify at openrouter.ai/models)</span>${cmdBlock('dstart',d.start_cmd)}
        <div class=mut style="font-size:12px;margin-top:4px">attach this package when prompted: <code>${esc(d.package)}</code></div></li>
      <li style="margin-top:8px"><b>paste the ${d.n_turns} turns in order</b>${turns}</li>
    </ol>${rem}</div>`;
}

// ---------- Runs ----------
async function viewRuns(){
  const app=document.getElementById('app'); app.innerHTML='<div class=card>'+loading('Loading run folders…')+'</div>';
  RUNS=await api('/api/runs');
  const items=RUNS.runs.map(r=>`<tr class=runrow data-run="${esc(r.name)}" onclick='openRun(${JSON.stringify(r.name)})'>
    <td><a class=runlink>${esc(r.name)}</a></td>
    <td><span class=tag>${esc(r.stage)}</span></td><td class=mut>${r.n_files} files</td></tr>`).join('');
  app.innerHTML=`<div class=card><h2>Run folders</h2>
    <table><thead><tr><th>Folder</th><th>Stage</th><th></th></tr></thead><tbody>${items}</tbody></table></div>
    <div class=card><details open id=promptdetails><summary><b>Prompt for this run</b> <span class=mut id=promptsum style="font-size:12px">— select a run</span></summary>
      <label class=chk style="margin-top:8px"><input type=checkbox id=pdisc checked> include methodology discussion <span class=mut>(operator debates method with the model; off = model self-proposes, you review &amp; confirm)</span></label>
      <div id=promptbox style="margin-top:8px"><p class=empty>Select a run to see its stage's prompt, split into turns.</p></div></details></div>
    <div class=row><div class=card style="flex:1"><h2>Files</h2><div id=tree class=filelist><p class=empty>Select a run.</p></div></div>
    <div class=card style="flex:2"><h2 id=vtitle>Viewer</h2><div id=viewer><p class=empty>Select a file.</p></div></div></div>`;
}
let RUN_CUR=null;
async function openRun(name){
  RUN_CUR=name;
  document.querySelectorAll('tr.runrow').forEach(tr=>tr.classList.toggle('active', tr.dataset.run===name));
  const pd=document.getElementById('pdisc'); if(pd) pd.onchange=()=>{if(RUN_CUR)loadRunPrompt(RUN_CUR);};
  loadRunPrompt(name);
  const {files}=await api('/api/tree?run='+encodeURIComponent(name));
  document.getElementById('tree').innerHTML=files.map(f=>`<a onclick='openFile(${JSON.stringify(f)})'>${f.split('/').slice(2).join('/')}</a>`).join('')||'<p class=empty>empty</p>';
}
async function loadRunPrompt(name){
  const box=document.getElementById('promptbox'); if(!box)return;
  const sum=document.getElementById('promptsum');
  const pd=document.getElementById('pdisc');
  const mode=(pd && !pd.checked)?'nodiscuss':'discuss';
  box.innerHTML=loading('Loading prompt…');
  const d=await api('/api/prompt?run='+encodeURIComponent(name)+'&mode='+mode);
  if(d.error){box.innerHTML='<p class=empty>'+esc(d.error)+'</p>';return;}
  if(sum) sum.innerHTML='— '+stageChip(d.stage)+' '+esc(d.label);
  const head=`<div class=savebox>
    <div><span class=mut>Model</span> <code>${esc(d.label)}</code></div>
    <div style="margin-top:4px"><span class=mut>Output folder</span> <code>operator/${esc(d.output_folder)}</code></div>
    <div style="margin-top:4px"><span class=mut>Report name</span> <code>${esc(d.report_name)}</code></div>
    ${d.doc?`<div class=mut style="font-size:12px;margin-top:4px">Source: <code>${esc(d.doc)}</code> · {MODEL} auto-filled with “${esc(d.label)}”</div>`:''}
  </div>`;
  if(!d.doc){box.innerHTML=head+'<p class=empty>No prompt template wired for this stage yet.</p>';return;}
  const chunks=(d.turns||[]).map((t,i)=>{
    const id='rp'+i;
    const body=t.paste
      ? `<pre id=${id} style="margin:6px 0">${esc(t.text)}</pre><button class=ghost onclick="copyText(document.getElementById('${id}').textContent,this)">Copy</button>`
      : `<p class=empty style="text-align:left;padding:6px 0">↳ operator-led — no fixed text to paste.</p>`;
    return `<details class=chunk ${i===0?'open':''}><summary><span class=substep>Turn ${i+1}</span>${esc(t.title)}</summary><div style="margin-top:6px">${body}</div></details>`;
  }).join('') || '<p class=empty>This prompt has no turns.</p>';
  const rem=(d.reminders||[]).length?`<details class=chunk><summary class=mut><span class=substep>Reminders</span>Operator reminders — do not paste (${d.reminders.length})</summary><ul class=mut style="font-size:12px">${d.reminders.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul></details>`:'';
  box.innerHTML=head+chunks+rem;
}
async function openFile(rel){
  const v=document.getElementById('viewer'); document.getElementById('vtitle').textContent=rel.split('/').pop();
  if(/\.(png|jpe?g|gif)$/i.test(rel)){v.innerHTML=`<img class=fig onload="this.style.opacity=1" src="/api/image?path=${encodeURIComponent(rel)}">`;return;}
  if(/\.(py|md|csv|json|txt|yaml|yml|log)$/i.test(rel)){const d=await api('/api/file?path='+encodeURIComponent(rel));v.innerHTML='<pre>'+esc(d.text)+'</pre>';return;}
  v.innerHTML='<p class=empty>Preview not supported for this file type.</p>';
}

// ---------- Compare ----------
let CMP={run:null,q:1};
async function viewCompare(){
  const app=document.getElementById('app');
  if(!RUNS) RUNS=await api('/api/runs');
  const runOpts=RUNS.runs.filter(r=>r.stage!=='origin(key)').map(r=>`<option>${r.name}</option>`).join('');
  app.innerHTML=`<div class=card><h2>Compare — validator vs. original, by question</h2>
    <div class=row><div><label>Run</label><select id=crun>${runOpts}</select></div></div>
    <div class=qnav id=qnav style="margin-top:12px"></div>
    <div id=ctitle class=mut style="margin-bottom:10px"></div>
    <div class=split><div><h3 id=vlab>Validator</h3><div id=vfigs></div></div>
      <div><h3>Original (key)</h3><div id=ofigs></div></div></div>
    <div style="margin-top:14px"><label>Notes for this question <span class=mut id=nsaved></span></label>
      <textarea id=qnote rows=4 style="width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--fg);border-radius:7px;padding:8px;font:13px system-ui"></textarea>
      <button class=ghost id=nsave style="margin-top:6px">Save note</button></div>
    </div>`;
  const qn=document.getElementById('qnav');
  qn.innerHTML=CFG.questions.map(q=>`<button data-q=${q.n}>${q.n}</button>`).join('');
  qn.querySelectorAll('button').forEach(b=>b.onclick=()=>{CMP.q=+b.dataset.q;loadCmp();});
  document.getElementById('crun').onchange=async()=>{CMP.run=document.getElementById('crun').value;await loadNotes();loadCmp();};
  document.getElementById('nsave').onclick=async()=>{
    await busy(document.getElementById('nsave'),'Saving…',async()=>{
      const r=await post('/api/notes',{run:CMP.run,q:CMP.q,text:document.getElementById('qnote').value});
      CMP.notes=r.notes; document.getElementById('nsaved').textContent='— saved ✓';
      setTimeout(()=>{const e=document.getElementById('nsaved');if(e)e.textContent='';},1500);
    });
  };
  CMP.run=document.getElementById('crun').value; CMP.q=1; await loadNotes(); loadCmp();
}
async function loadNotes(){const d=await api('/api/notes?run='+encodeURIComponent(CMP.run));CMP.notes=d.notes||{};}
async function loadCmp(){
  document.querySelectorAll('#qnav button').forEach(b=>b.classList.toggle('active',+b.dataset.q===CMP.q));
  const d=await api(`/api/figures?run=${encodeURIComponent(CMP.run)}&q=${CMP.q}`);
  document.getElementById('ctitle').innerHTML=`<b>Q${d.q}</b> — ${esc(d.topic)} <span class=tag>orig Q${d.orig}</span>`;
  const imgs=(a)=>a.length?a.map(p=>`<img class=fig onload="this.style.opacity=1" src="/api/image?path=${encodeURIComponent(p)}" title="${p.split('/').pop()}">`).join(''):'<p class=empty>no figures found</p>';
  document.getElementById('vfigs').innerHTML=imgs(d.validator);
  document.getElementById('ofigs').innerHTML=imgs(d.original);
  const note=(CMP.notes||{})[String(CMP.q)]||'';
  document.getElementById('qnote').value=note;
  document.getElementById('nsaved').textContent=note?'— has a saved note':'';
}

// ---------- Scorecards ----------
async function viewScore(){
  const app=document.getElementById('app');
  if(!RUNS) RUNS=await api('/api/runs');
  const runOpts=RUNS.runs.filter(r=>r.stage!=='origin(key)').map(r=>`<option value="${r.name}" data-stage="${r.stage}" data-label="${r.label}">${r.name}</option>`).join('');
  const cards=RUNS.scorecards.map(c=>`<a onclick='openCard(${JSON.stringify(c.rel)})'>${c.name}</a>`).join('')||'<p class=empty>none yet</p>';
  app.innerHTML=`<div class=row>
    <div class=card style="flex:1"><h2>Generate skeleton</h2>
      <label>Run</label><select id=srun>${runOpts}</select>
      <button class=go id=sgo>Generate scorecard</button>
      <div id=sout style="margin-top:10px"></div>
      <h2 style="margin-top:18px">Existing</h2><div class=filelist id=scards>${cards}</div></div>
    <div class=card style="flex:2"><h2 id=stitle>Scorecard</h2><div id=sview><p class=empty>Select or generate a scorecard.</p></div></div></div>`;
  document.getElementById('sgo').onclick=async()=>{
    await busy(document.getElementById('sgo'),'Generating…',async()=>{
      const sel=document.getElementById('srun').selectedOptions[0];
      document.getElementById('sout').innerHTML=loading('Generating scorecard…');
      const r=await post('/api/make_scorecard',{run:sel.value,stage:sel.dataset.stage,model:sel.dataset.label});
      document.getElementById('sout').innerHTML='<pre>'+esc(r.stdout||r.stderr)+'</pre>';
      RUNS=await api('/api/runs'); if(r.rel) openCard(r.rel); viewScore();
    });
  };
}
async function openCard(rel){
  const d=await api('/api/scorecard?path='+encodeURIComponent(rel));
  document.getElementById('stitle').textContent=rel.split('/').pop();
  document.getElementById('sview').innerHTML='<pre>'+esc(d.text)+'</pre>';
}
// ---------- Setup (study cartridge editor) ----------
async function viewSetup(){
  const app=document.getElementById('app'); app.innerHTML='<div class=card>'+loading('Loading study cartridge…')+'</div>';
  const r=await api('/api/study');
  const s=(r.study&&r.study.study)||{};
  const ds=s.dataset||{}, aux=ds.aux||{}, gs=s.given_solution||{}, qs=s.questions||{}, hc=s.held_constants||{}, og=s.original||{}, dl=s.deliverable||{}, mg=dl.method_guide||{};
  const addv=(s.additional||[]).map(it=>[(it.name||''),(it.file||''),(it.note||'')].join(' :: ')).join('\n');
  const tstyle="width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--fg);border-radius:7px;padding:8px;font:13px system-ui";
  const ti=(id,label,val,ph='')=>`<label>${label}</label><input type=text id=${id} value="${escA(val==null?'':String(val))}" placeholder="${escA(ph)}">`;
  const ta=(id,label,val,rows=3)=>`<label>${label}</label><textarea id=${id} rows=${rows} style="${tstyle}">${esc(val||'')}</textarea>`;
  const tog=(id,checked,label)=>`<label class=chk><input type=checkbox id=${id} ${checked?'checked':''}> ${label}</label>`;
  app.innerHTML=`
  <div class=card><h2>Setup — study cartridge ${r.exists?'':'<span class="pill no">no study.yaml yet</span>'}</h2>
    <p class=mut style="font-size:12px">Everything specific to this study. The engine (stages, blinding, dispatch) stays in vp_config.yaml. File fields are repo-relative paths. See docs/GENERALIZATION_DESIGN.md.</p>
    ${ti('st_title','Study title',s.title)}
    ${ti('st_overview','Study overview file',s.overview_file,'shared/STUDY_OVERVIEW_all.md')}
  </div>
  <div class=card><h2>Dataset</h2>
    <div class=row><div>${ti('st_source','Source file (original)',ds.source)}</div><div>${ti('st_main','Main sample name',ds.main_name)}</div></div>
    <div class=row><div>${ti('st_merge','Merge key',ds.merge_key)}</div><div>${ti('st_formats','Formats (comma-sep)',(ds.formats||[]).join(', '))}</div></div>
    <div class=row><div>${ti('st_codebook','Codebook file',ds.codebook)}</div><div>${ti('st_subset','Subset overview file',ds.subset_overview)}</div></div>
    ${ta('st_orient','Data-orientation paragraph — may use {MAIN_DATASET} {FORMATS} {CODEBOOK} {SUBSET_OVERVIEW}',ds.orientation,3)}
    ${tog('st_aux_en',aux.enabled,'aux dataset (optional secondary sample)')}
    <div class=row><div>${ti('st_aux_name','Aux dataset name',aux.name)}</div><div>${ti('st_aux_note','Aux note',aux.note)}</div></div>
  </div>
  <div class=card><h2>Given solution <span class=mut style="font-size:12px">— optional module</span></h2>
    ${tog('st_gs_en',gs.enabled,'study hands the model a fixed solution it must not re-derive')}
    ${ti('st_gs_gloss','Glossary file',gs.glossary)}
    ${ta('st_gs_arts','Artifact files (one per line)',(gs.artifacts||[]).join('\n'),2)}
    ${ta('st_gs_note','Given-solution note — may use {MERGE_KEY} {SOLUTION_GLOSSARY}',gs.note,3)}
  </div>
  <div class=card><h2>Additional datasets <span class=mut style="font-size:12px">— optional; one per line as  name :: file :: note</span></h2>
    ${ta('st_add','Extra provided inputs (e.g. a prof-supplied CFA solution)',addv,3)}
  </div>
  <div class=card><h2>Questions</h2>
    <div class=row><div>${ti('st_q_file','Questions file',qs.file)}</div><div>${ti('st_q_count','Count',qs.count)}</div><div>${ti('st_q_map','Q-map (Compare)',qs.map)}</div></div>
  </div>
  <div class=card><h2>Held-constants</h2>
    ${ti('st_hc_file','Held-constants file',hc.file)}
    ${ta('st_hc_sum','Summary (inline list shown in prompt)',hc.summary,2)}
    ${ta('st_hc_qa','QA group structure to verify Ns for',hc.qa_groups,2)}
  </div>
  <div class=card><h2>Original investigation</h2>
    <div class=row><div>${ti('st_og_meth','Methodology file (replication target)',og.methodology_file)}</div><div>${ti('st_og_key','Results key (held back)',og.results_key)}</div></div>
    <div class=row><div>${ti('st_og_model','Original model',og.model)}</div><div>${ti('st_og_vendor','Vendor',og.vendor)}</div></div>
  </div>
  <div class=card><h2>Deliverable</h2>
    ${ti('st_dl_report','Report name pattern',dl.report_name,'{MODEL}_Report.docx')}
    ${ta('st_dl_spec','Per-question reporting spec',dl.reporting_spec,3)}
    ${tog('st_mg_en',mg.enabled,'method guide (optional special reporting method)')}
    <div class=row><div>${ti('st_mg_name','Method-guide name',mg.name)}</div><div>${ti('st_mg_file','Method-guide file',mg.file)}</div></div>
  </div>
  <div class=card>
    <button class=go id=st_save>Save study.yaml</button>
    <button class=ghost id=st_pre style="margin-left:8px">Run preflight</button>
    <span class=mut id=st_msg style="margin-left:10px;font-size:12px"></span>
    <div id=st_preout style="margin-top:12px"></div>
  </div>
  <div class=card><h2>Prompt preview</h2>
    <div class=row><div><label>Stage</label><select id=st_pvstage>${CFG.stages.map(x=>`<option>${esc(x)}</option>`).join('')}</select></div>
      <div><label>Sample model label</label><input type=text id=st_pvlabel value="SampleModel"></div></div>
    <label class=chk><input type=checkbox id=st_pvdisc checked> include methodology discussion</label>
    <div><button class=ghost id=st_pvgo>Preview prompt</button></div>
    <p class=mut style="font-size:12px;margin-top:6px">Preview uses the last <b>saved</b> cartridge — save first to see edits.</p>
    <div id=st_pvout style="margin-top:10px"><p class=empty>Pick a stage and preview.</p></div>
  </div>`;
  document.getElementById('st_save').onclick=async()=>{
    await busy(document.getElementById('st_save'),'Saving…',async()=>{
      const res=await post('/api/study',{study:collectStudy()});
      const msg=document.getElementById('st_msg');
      msg.textContent=res.ok?'Saved ✓ — applies on next prompt render':('Error: '+(res.error||'save failed'));
      setTimeout(()=>{const e=document.getElementById('st_msg');if(e)e.textContent='';},2800);
    });
  };
  document.getElementById('st_pre').onclick=async()=>{
    await busy(document.getElementById('st_pre'),'Checking…',async()=>{
      const out=document.getElementById('st_preout'); out.innerHTML=loading('Running preflight…');
      out.innerHTML=renderPreflight(await api('/api/preflight'));
    });
  };
  document.getElementById('st_pvgo').onclick=async()=>{
    await busy(document.getElementById('st_pvgo'),'Rendering…',async()=>{
      const out=document.getElementById('st_pvout'); out.innerHTML=loading('Rendering…');
      const stage=document.getElementById('st_pvstage').value;
      const label=document.getElementById('st_pvlabel').value||'SampleModel';
      const mode=document.getElementById('st_pvdisc').checked?'discuss':'nodiscuss';
      const d=await api(`/api/study_preview?stage=${encodeURIComponent(stage)}&mode=${mode}&label=${encodeURIComponent(label)}`);
      if(!d.doc){out.innerHTML='<p class=empty>No prompt wired for this stage.</p>';return;}
      out.innerHTML=`<div class=mut style="font-size:12px;margin-bottom:6px">output: <code>operator/${esc(d.output_folder)}</code> · report: <code>${esc(d.report_name)}</code></div>`+
        d.turns.map((t,i)=>`<details class=chunk ${i===0?'open':''}><summary><span class=substep>Turn ${i+1}</span>${esc(t.title)}</summary><div style="margin-top:6px">${t.paste?('<pre>'+esc(t.text)+'</pre>'):'<p class=empty style="text-align:left">↳ operator-led — no fixed text.</p>'}</div></details>`).join('');
    });
  };
}
function collectStudy(){
  const gv=(id)=>document.getElementById(id).value;
  const gc=(id)=>document.getElementById(id).checked;
  return {
    title:gv('st_title'), overview_file:gv('st_overview'),
    dataset:{ source:gv('st_source'), main_name:gv('st_main'), merge_key:gv('st_merge'),
      formats:gv('st_formats').split(',').map(x=>x.trim()).filter(Boolean),
      codebook:gv('st_codebook'), subset_overview:gv('st_subset'), orientation:gv('st_orient'),
      aux:{ enabled:gc('st_aux_en'), name:gv('st_aux_name'), note:gv('st_aux_note') } },
    given_solution:{ enabled:gc('st_gs_en'), glossary:gv('st_gs_gloss'),
      artifacts:gv('st_gs_arts').split('\n').map(x=>x.trim()).filter(Boolean), note:gv('st_gs_note') },
    questions:{ file:gv('st_q_file'), count:parseInt(gv('st_q_count'))||0, map:gv('st_q_map') },
    held_constants:{ file:gv('st_hc_file'), summary:gv('st_hc_sum'), qa_groups:gv('st_hc_qa') },
    original:{ methodology_file:gv('st_og_meth'), results_key:gv('st_og_key'), model:gv('st_og_model'), vendor:gv('st_og_vendor') },
    additional:gv('st_add').split('\n').map(l=>l.trim()).filter(Boolean).map(l=>{
      const p=l.split('::').map(x=>x.trim());
      return {name:p[0]||'', file:p[1]||'', note:p[2]||''};
    }),
    deliverable:{ report_name:gv('st_dl_report'), reporting_spec:gv('st_dl_spec'),
      method_guide:{ enabled:gc('st_mg_en'), name:gv('st_mg_name'), file:gv('st_mg_file') } }
  };
}
function renderPreflight(d){
  const row=(c)=>`<tr><td>${c.ok===null?'<span class="pill no">—</span>':(c.ok?'<span class="pill yes">✓</span>':'<span class="pill no">✗</span>')}</td><td>${esc(c.label||c.stage)}</td><td class=mut style="font-size:12px">${esc(c.detail||'')}${c.path?(' · <code>'+esc(c.path)+'</code>'):''}</td></tr>`;
  const banner=d.ok?'<div class="banner ok">✓ Preflight passed — files present and prompts fill clean</div>':'<div class="banner bad">⚠ Preflight found issues — see below</div>';
  return banner+'<table><thead><tr><th></th><th>Check</th><th>Detail</th></tr></thead><tbody>'+
    d.checks.map(row).join('')+d.renders.map(row).join('')+'</tbody></table>';
}
boot();
</script>
</body></html>"""


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Validation Pipeline GUI → {url}")
    print(f"  repo: {REPO}")
    print("  (Ctrl-C to stop)")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
