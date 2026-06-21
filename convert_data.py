#!/usr/bin/env python3
"""
convert_data.py — deterministic, verified, lossless-by-spec data converter.

A validation pipeline should not assume every lab uses SPSS. This reads a source
dataset in any common format and emits one or more analysis-ready derivatives
plus a metadata sidecar — so the *original* file stays the single source of
truth and the derivatives are reproducible from it (regenerate any time; never
hand-edit). After writing, it **reads each derivative back and verifies it
matches the source cell-for-cell** (NaN pattern, max numeric diff, strings).

Reads (auto-detected by extension):
  • SPSS  .sav .zsav .por      (pyreadstat — value/variable labels, missing)
  • Stata .dta                 (pyreadstat — labels too)
  • SAS   .sas7bdat .xpt       (pyreadstat)
  • Flat  .csv .tsv .xlsx .parquet  (pandas — thinner metadata, no value labels)

Writes (choose with --formats; sidecar + codebook always written):
  • csv      — universal, human-readable. Best for *exploring*. Default.
               Loses dtypes (text) — the sidecar restores them; verification
               confirms values are identical.
  • parquet  — typed, compressed, language-agnostic (Arrow: Python/R/Julia).
               Best *analysis* companion; preserves dtypes. Recommend with csv.

Label handling (SPSS/Stata sources): csv/parquet are written CODED by default
(raw numeric codes, round-trips to the source); --labeled applies value labels
(1 → "Monogamy"). Either way the value labels live in the sidecar.

Determinism: csv is byte-identical on re-run; parquet is content-identical.

Usage:
    python3 convert_data.py SOURCE [--out STEM] [--formats csv parquet]
                            [--labeled] [--na-token ""] [--float-format FMT] [--json]

Default SOURCE: the `origin.source_data` path in vp_config.yaml.
Requires: pyreadstat, pandas; parquet also needs pyarrow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError as e:  # pragma: no cover
    sys.stderr.write(f"missing dependency: {e}. pip install pandas numpy\n")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

OUT_FORMATS = ("csv", "parquet")
LABEL_BEARING = {".sav", ".zsav", ".por", ".dta"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def default_source(repo: Path):
    cfg = HERE / "vp_config.yaml"
    if cfg.exists():
        try:
            import yaml
            src = yaml.safe_load(cfg.read_text()).get("origin", {}).get("source_data")
            if src:
                return (repo / src).resolve()
        except Exception:
            pass
    return None


# --------------------------------------------------------------------------- #
# Reading (format-agnostic; returns df + optional pyreadstat metadata)
# --------------------------------------------------------------------------- #
def read_source(path: Path, labeled: bool):
    ext = path.suffix.lower()
    try:
        import pyreadstat
    except ImportError:
        pyreadstat = None
    readers = {}
    if pyreadstat:
        readers = {
            ".sav": pyreadstat.read_sav, ".zsav": pyreadstat.read_sav,
            ".por": pyreadstat.read_por, ".dta": pyreadstat.read_dta,
            ".sas7bdat": pyreadstat.read_sas7bdat,
            ".xpt": pyreadstat.read_xport, ".xport": pyreadstat.read_xport,
        }
    if ext in readers:
        kw = {"apply_value_formats": labeled} if ext in LABEL_BEARING else {}
        return readers[ext](str(path), **kw)
    if ext == ".csv":
        return pd.read_csv(path), None
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t"), None
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path), None
    if ext == ".parquet":
        return pd.read_parquet(path), None
    raise SystemExit(f"unsupported source format: {ext}")


# --------------------------------------------------------------------------- #
# Verification — does the derivative match the source data cell-for-cell?
# --------------------------------------------------------------------------- #
def read_back(path: Path):
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    return None


def verify_against_source(src_df, out_path: Path, tol: float = 1e-9):
    """Read a derivative back and compare to the in-memory source frame.

    Numeric columns are compared within `tol` — csv stores floats as text, so a
    human-readable value can round-trip to within float64 epsilon (~1e-16) rather
    than bit-for-bit; that is 'identical to float precision', not a real change.
    Parquet is typed and matches bit-for-bit (max diff 0.0). Strings and the
    NaN pattern must match exactly.
    """
    out_df = read_back(out_path)
    if out_df is None:
        return {"ok": None, "reason": "format not read-verifiable"}
    if list(src_df.columns) != list(out_df.columns):
        return {"ok": False, "reason": "columns differ"}
    if src_df.shape != out_df.shape:
        return {"ok": False, "reason": f"shape {src_df.shape} vs {out_df.shape}"}
    max_diff = 0.0
    str_mismatch = 0
    nan_ok = True
    for col in src_df.columns:
        a, b = src_df[col], out_df[col]
        amask, bmask = a.isna().values, b.isna().values
        if not np.array_equal(amask, bmask):
            nan_ok = False
        keep = ~amask & ~bmask
        av, bv = a[keep], b[keep]
        an = pd.to_numeric(av, errors="coerce")
        bn = pd.to_numeric(bv, errors="coerce")
        if len(av) and an.notna().all() and bn.notna().all():
            d = float(np.abs(an.values - bn.values).max()) if len(an) else 0.0
            max_diff = max(max_diff, d)
        else:
            str_mismatch += int((av.astype(str).values != bv.astype(str).values).sum())
    ok = nan_ok and max_diff <= tol and str_mismatch == 0
    return {"ok": ok, "max_numeric_diff": max_diff, "exact": max_diff == 0.0,
            "tolerance": tol, "string_mismatches": str_mismatch,
            "nan_pattern_ok": nan_ok}


# --------------------------------------------------------------------------- #
# Metadata sidecar
# --------------------------------------------------------------------------- #
def build_meta(df, meta, source: Path, labeled: bool) -> dict:
    cols = list(df.columns)
    var_labels, value_labels, measures, missing_ranges = {}, {}, {}, {}
    if meta is not None:
        var_labels = dict(zip(meta.column_names, meta.column_labels)) \
            if meta.column_labels else {}
        name_to_set = getattr(meta, "variable_to_label", {}) or {}
        label_sets = getattr(meta, "value_labels", {}) or {}
        for c in meta.column_names:
            sn = name_to_set.get(c)
            if sn and sn in label_sets:
                value_labels[c] = {str(k): v for k, v in label_sets[sn].items()}
        measures = getattr(meta, "variable_measure", {}) or {}
        missing_ranges = getattr(meta, "missing_ranges", {}) or {}
    variables = {}
    for c in cols:
        variables[c] = {
            "dtype": str(df[c].dtype),
            "label": var_labels.get(c) or None,
            "measure": measures.get(c),
            "value_labels": value_labels.get(c) or None,
            "missing_ranges": missing_ranges.get(c) or None,
        }
    return {
        "source_file": source.name,
        "source_sha256": sha256(source),
        "source_format": source.suffix.lower(),
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "csv_mode": "labeled" if labeled else "coded",
        "encoding": "utf-8",
        "columns": cols,
        "variables": variables,
        "file_label": getattr(meta, "file_label", None) if meta is not None else None,
        "note": ("Reproducible derivative of the source (single source of truth). "
                 "Regenerate with convert_data.py; do not hand-edit."),
    }


# --------------------------------------------------------------------------- #
def write_csv(df, path, na, ff):
    df.to_csv(path, index=False, encoding="utf-8", na_rep=na,
              float_format=ff, lineterminator="\n")


def write_parquet(df, path, na, ff):
    try:
        df.to_parquet(path, index=False)
    except Exception as e:
        raise SystemExit(f"parquet write failed ({e}); pip install pyarrow")


WRITERS = {"csv": write_csv, "parquet": write_parquet}
EXT = {"csv": ".csv", "parquet": ".parquet"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic, verified multi-format converter.")
    ap.add_argument("source", nargs="?", default=None)
    ap.add_argument("--out", default=None, help="output stem (default: source stem)")
    ap.add_argument("--formats", nargs="+", default=["csv"], choices=OUT_FORMATS,
                    help="output formats (default: csv). e.g. --formats csv parquet")
    ap.add_argument("--labeled", action="store_true",
                    help="apply value labels (label-bearing sources only)")
    ap.add_argument("--na-token", default="")
    ap.add_argument("--float-format", default=None,
                    help="csv float format (default: round-trippable shortest repr)")
    ap.add_argument("--json", action="store_true", help="emit a machine-readable summary")
    args = ap.parse_args(argv)

    source = Path(args.source).resolve() if args.source else default_source(REPO)
    if not source or not source.is_file():
        sys.stderr.write(f"source not found: {source}\n")
        return 1

    df, meta = read_source(source, args.labeled)
    if args.labeled and meta is None:
        sys.stderr.write("note: --labeled ignored (source carries no value labels)\n")

    stem = Path(args.out).resolve() if args.out else source.with_suffix("")
    Path(stem).parent.mkdir(parents=True, exist_ok=True)

    outputs = []
    for fmt in args.formats:
        path = Path(f"{stem}{EXT[fmt]}")
        WRITERS[fmt](df, path, args.na_token, args.float_format)
        verify = verify_against_source(df, path)
        outputs.append({"format": fmt, "path": str(path), "name": path.name,
                        "verify": verify})

    sidecar = build_meta(df, meta, source, args.labeled)
    sidecar["na_token"] = args.na_token
    sidecar["outputs"] = [o["name"] for o in outputs]
    sidecar["verification"] = {o["format"]: o["verify"] for o in outputs}
    meta_path = Path(f"{stem}.meta.json")
    meta_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False))

    rows = []
    for c in sidecar["columns"]:
        v = sidecar["variables"][c]
        vl = v["value_labels"]
        rows.append({"variable": c, "label": v["label"] or "", "dtype": v["dtype"],
                     "measure": v["measure"] or "",
                     "value_labels": "; ".join(f"{k}={lab}" for k, lab in vl.items()) if vl else "",
                     "missing": json.dumps(v["missing_ranges"]) if v["missing_ranges"] else ""})
    cb_path = Path(f"{stem}.codebook.csv")
    pd.DataFrame(rows).to_csv(cb_path, index=False, encoding="utf-8", lineterminator="\n")

    summary = {
        "source": source.name, "source_sha256": sidecar["source_sha256"],
        "source_format": sidecar["source_format"],
        "n_rows": sidecar["n_rows"], "n_cols": sidecar["n_cols"],
        "mode": sidecar["csv_mode"], "outputs": outputs,
        "sidecar": meta_path.name, "codebook": cb_path.name,
        "all_verified": all(o["verify"].get("ok") for o in outputs),
    }
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    n_vl = sum(1 for c in sidecar["columns"] if sidecar["variables"][c]["value_labels"])
    print(f"Converted {source.name} ({sidecar['source_format']})  →  "
          f"{', '.join(o['name'] for o in outputs)}  "
          f"({sidecar['n_rows']} rows × {sidecar['n_cols']} cols, {sidecar['csv_mode']})")
    for o in outputs:
        v = o["verify"]
        if v.get("ok"):
            how = "bit-for-bit" if v.get("exact") else f"to float precision (max diff {v['max_numeric_diff']:.1e})"
            print(f"  ✓ {o['format']}: values identical to source — {how}; strings exact, NaN pattern matches")
        else:
            print(f"  ✗ {o['format']}: MISMATCH — {v}")
    print(f"  sidecar:  {meta_path.name}  ({n_vl} vars with value labels)")
    print(f"  codebook: {cb_path.name}")
    print(f"  source sha256: {sidecar['source_sha256'][:16]}…  (provenance anchor)")
    print("  The source remains the single source of truth; derivatives are reproducible from it.")
    return 0 if summary["all_verified"] else 2


if __name__ == "__main__":
    sys.exit(main())
