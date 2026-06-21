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


def parse_prompt_turns(doc_path: Path):
    """Split a staged prompt doc into ordered turns + operator reminders.

    Each '## Turn N — title' becomes a turn; its paste text is the fenced code
    block (turns with no block, e.g. an operator-led discussion, are marked
    paste=False). The '## Operator reminders (do not paste)' section is returned
    separately and is NEVER shown as a paste block.
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
        low = head.lower()
        if low.startswith("turn"):
            cb = re.search(r"```(.*?)```", body, re.S)
            turns.append({"title": head,
                          "text": cb.group(1).strip() if cb else "",
                          "paste": bool(cb)})
        elif low.startswith("operator reminder"):
            reminders = [l.strip("-* ").strip() for l in body.splitlines()
                         if l.strip().startswith(("-", "*"))]
    return turns, reminders


def render_dispatch(cfg, prov, stage):
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
    turns, reminders = parse_prompt_turns(REPO / doc) if doc else ([], [])
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
            })

        if u.path == "/api/runs":
            return self._send(200, {"runs": list_runs(),
                                    "scorecards": list_scorecards()})

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
                                                  j.get("provenance"), stage)
            return self._send(200, res)

        if u.path == "/api/notes":
            return self._send(200, {"notes": save_note(payload.get("run", ""),
                                                        payload.get("q"),
                                                        payload.get("text", ""))})

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
.row{display:flex;gap:14px;flex-wrap:wrap}
.row>div{flex:1;min-width:180px}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);margin-right:16px;margin-top:10px}
.chk input{width:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:500}
.pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}
.yes{background:rgba(63,185,80,.15);color:var(--ok)}
.no{background:rgba(139,148,158,.12);color:var(--mut)}
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
.qnav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.qnav button{width:34px;height:34px;border-radius:7px;border:1px solid var(--line);background:var(--panel2);color:var(--fg);cursor:pointer}
.qnav button.active{background:var(--acc);color:#06122b;border-color:var(--acc);font-weight:700}
.banner{padding:10px 14px;border-radius:8px;margin-bottom:12px;font-weight:600}
.banner.ok{background:rgba(63,185,80,.13);color:var(--ok);border:1px solid rgba(63,185,80,.3)}
.banner.bad{background:rgba(248,81,73,.13);color:var(--bad);border:1px solid rgba(248,81,73,.3)}
.empty{color:var(--mut);font-style:italic;padding:20px;text-align:center}
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
function copyText(t,btn){navigator.clipboard.writeText(t).then(()=>{const o=btn.textContent;btn.textContent='Copied ✓';setTimeout(()=>btn.textContent=o,1200);});}

async function boot(){
  CFG=await api('/api/config');
  document.getElementById('repo').textContent=CFG.repo;
  document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>{
    document.querySelectorAll('#nav button').forEach(x=>x.classList.remove('active'));
    b.classList.add('active'); show(b.dataset.v);
  });
  show('dashboard');
}
function show(v){const f={dashboard:viewDash,convert:viewConvert,build:viewBuild,runs:viewRuns,compare:viewCompare,scorecards:viewScore}[v];f();}

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
    <span class=chk><input type=checkbox id=cfcsv checked> csv <span class=mut>(human-readable, for exploring)</span></span>
    <span class=chk><input type=checkbox id=cfpq checked> parquet <span class=mut>(typed, for analysis)</span></span>
    <span class=chk style="margin-top:10px"><input type=checkbox id=clab> apply value labels <span class=mut>(1 → "Monogamy"; default = coded codes)</span></span>
    <div><button class=go id=cgo>Convert &amp; verify</button></div>
    <div id=cout style="margin-top:14px"></div></div>`;
  document.getElementById('cgo').onclick=async()=>{
    const fmts=[]; if(document.getElementById('cfcsv').checked)fmts.push('csv'); if(document.getElementById('cfpq').checked)fmts.push('parquet');
    const out=document.getElementById('cout');
    if(!fmts.length){out.innerHTML='<div class="banner bad">Pick at least one format.</div>';return;}
    out.innerHTML='<p class=mut>Converting + verifying…</p>';
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
  };
}

// ---------- Dashboard ----------
async function viewDash(){
  const app=document.getElementById('app'); app.innerHTML='<div class=card><h2>Loading…</h2></div>';
  const {grid}=await api('/api/dashboard');
  const badge=(b)=>b?'<span class="pill yes">✓</span>':'<span class="pill no">·</span>';
  let rows=grid.map(g=>`<tr>
    <td><span class=tag>${g.stage}</span></td>
    <td>${esc(g.model)} <span class=mut style="font-size:11px">${g.type||''}</span></td>
    <td>${badge(g.packaged)}</td><td>${badge(g.returned)}</td><td>${badge(g.graded)}</td>
    <td class=mut style="font-size:11px">${esc(g.note||'')}</td></tr>`).join('');
  app.innerHTML=`<div class=card><h2>Run status — stage × model</h2>
    <table><thead><tr><th>Stage</th><th>Model</th><th>Packaged</th><th>Returned</th><th>Graded</th><th>Note</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <p class=mut style="margin-top:10px">Packaged = a blinding-passed package was built · Returned = results are in the run folder · Graded = a scorecard exists.</p></div>`;
}

// ---------- Build ----------
function viewBuild(){
  const app=document.getElementById('app');
  const stageOpts=CFG.stages.map(s=>`<option>${s}</option>`).join('');
  app.innerHTML=`<div class=card><h2>Build &amp; blinding-gate a package</h2>
    <div class=row>
      <div><label>Stage</label><select id=bstage>${stageOpts}</select></div>
      <div><label>Model</label><select id=bmodel></select></div>
    </div>
    <span class=chk><input type=checkbox id=bdry checked> dry-run (validate, publish nothing)</span>
    <span class=chk><input type=checkbox id=bforce> force (override a HARD FAIL — logged)</span>
    <div><button class=go id=bgo>Build package</button></div>
    <div id=bout style="margin-top:14px"></div></div>`;
  const fill=()=>{const s=document.getElementById('bstage').value;
    document.getElementById('bmodel').innerHTML=CFG.roster[s].map(m=>`<option value="${esc(m.model)}">${esc(m.model)} — ${m.type}/${esc(m.license||'')}</option>`).join('');};
  document.getElementById('bstage').onchange=fill; fill();
  document.getElementById('bgo').onclick=async()=>{
    const out=document.getElementById('bout'); out.innerHTML='<p class=mut>Building…</p>';
    const r=await post('/api/build',{stage:document.getElementById('bstage').value,
      model:document.getElementById('bmodel').value,
      dry_run:document.getElementById('bdry').checked, force:document.getElementById('bforce').checked});
    const j=r.json||{}; const ok=r.returncode===0 && !j.blocked;
    const banner=j.blocked?'<div class="banner bad">⛔ BLOCKED by blinding gate — nothing published</div>'
      :(r.returncode===0?'<div class="banner ok">✓ '+(j.lint==='pass'?'Blinding PASS':'Forced override')+' — ready to dispatch</div>'
      :'<div class="banner bad">Error (exit '+r.returncode+')</div>');
    let disp='';
    if(r.dispatch){disp=renderDispatch(r.dispatch);}
    else if(document.getElementById('bdry').checked){
      disp='<p class=mut style="margin-top:10px">Uncheck dry-run to publish the package + empty output folder and get the dispatch steps.</p>';
    }
    out.innerHTML=banner+'<pre>'+esc((j.log||[]).join('\n')||r.stdout||r.stderr)+'</pre>'+disp;
  };
}
function cmdBlock(id,text){return `<pre id=${id} style="margin:4px 0">${esc(text)}</pre>`+
  `<button class=ghost onclick="copyText(document.getElementById('${id}').textContent,this)">Copy</button>`;}
function renderDispatch(d){
  let turns=(d.turns||[]).map((t,i)=>{
    if(t.paste) return `<div style="margin:10px 0"><div class=mut style="font-size:12px;margin-bottom:3px">${esc(t.title)}</div>${cmdBlock('turn'+i,t.text)}</div>`;
    return `<div style="margin:10px 0"><div class=mut style="font-size:12px">${esc(t.title)}</div><p class=empty style="text-align:left;padding:6px 0">↳ operator-led — no fixed text to paste.</p></div>`;
  }).join('');
  let rem=(d.reminders||[]).length?`<details style="margin-top:10px"><summary class=mut>Operator reminders (do not paste — ${d.reminders.length})</summary><ul class=mut style="font-size:12px">${d.reminders.map(x=>'<li>'+esc(x)+'</li>').join('')}</ul></details>`:'';
  return `<div class=card style="margin-top:12px;background:var(--panel2)">
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
  const app=document.getElementById('app'); app.innerHTML='<div class=card><h2>Loading…</h2></div>';
  RUNS=await api('/api/runs');
  const items=RUNS.runs.map(r=>`<tr><td><a onclick="openRun('${r.name}')">${r.name}</a></td>
    <td><span class=tag>${r.stage}</span></td><td class=mut>${r.n_files} files</td></tr>`).join('');
  app.innerHTML=`<div class=card><h2>Run folders</h2>
    <table><thead><tr><th>Folder</th><th>Stage</th><th></th></tr></thead><tbody>${items}</tbody></table></div>
    <div class=row><div class=card style="flex:1"><h2>Files</h2><div id=tree class=filelist><p class=empty>Select a run.</p></div></div>
    <div class=card style="flex:2"><h2 id=vtitle>Viewer</h2><div id=viewer><p class=empty>Select a file.</p></div></div></div>`;
}
async function openRun(name){
  const {files}=await api('/api/tree?run='+encodeURIComponent(name));
  document.getElementById('tree').innerHTML=files.map(f=>`<a onclick='openFile(${JSON.stringify(f)})'>${f.split('/').slice(2).join('/')}</a>`).join('')||'<p class=empty>empty</p>';
}
async function openFile(rel){
  const v=document.getElementById('viewer'); document.getElementById('vtitle').textContent=rel.split('/').pop();
  if(/\.(png|jpe?g|gif)$/i.test(rel)){v.innerHTML=`<img class=fig src="/api/image?path=${encodeURIComponent(rel)}">`;return;}
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
    const r=await post('/api/notes',{run:CMP.run,q:CMP.q,text:document.getElementById('qnote').value});
    CMP.notes=r.notes; document.getElementById('nsaved').textContent='— saved ✓';
    setTimeout(()=>{const e=document.getElementById('nsaved');if(e)e.textContent='';},1500);
  };
  CMP.run=document.getElementById('crun').value; CMP.q=1; await loadNotes(); loadCmp();
}
async function loadNotes(){const d=await api('/api/notes?run='+encodeURIComponent(CMP.run));CMP.notes=d.notes||{};}
async function loadCmp(){
  document.querySelectorAll('#qnav button').forEach(b=>b.classList.toggle('active',+b.dataset.q===CMP.q));
  const d=await api(`/api/figures?run=${encodeURIComponent(CMP.run)}&q=${CMP.q}`);
  document.getElementById('ctitle').innerHTML=`<b>Q${d.q}</b> — ${esc(d.topic)} <span class=tag>orig Q${d.orig}</span>`;
  const imgs=(a)=>a.length?a.map(p=>`<img class=fig src="/api/image?path=${encodeURIComponent(p)}" title="${p.split('/').pop()}">`).join(''):'<p class=empty>no figures found</p>';
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
    const sel=document.getElementById('srun').selectedOptions[0];
    document.getElementById('sout').innerHTML='<p class=mut>Generating…</p>';
    const r=await post('/api/make_scorecard',{run:sel.value,stage:sel.dataset.stage,model:sel.dataset.label});
    document.getElementById('sout').innerHTML='<pre>'+esc(r.stdout||r.stderr)+'</pre>';
    RUNS=await api('/api/runs'); if(r.rel) openCard(r.rel); viewScore();
  };
}
async function openCard(rel){
  const d=await api('/api/scorecard?path='+encodeURIComponent(rel));
  document.getElementById('stitle').textContent=rel.split('/').pop();
  document.getElementById('sview').innerHTML='<pre>'+esc(d.text)+'</pre>';
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
