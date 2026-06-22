#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
STAMP="$VENV/.rrg-requirements"

if [[ ! -x "$VENV/bin/python" ]]; then
  PYTHON=""
  for candidate in "${RRG_PYTHON:-}" python3 /usr/bin/python3; do
    [[ -n "$candidate" ]] || continue
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
      'import sys, ensurepip, xml.parsers.expat; raise SystemExit(sys.version_info < (3, 9))' \
      >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
  if [[ -z "$PYTHON" ]]; then
    echo "No working Python 3.9+ installation was found." >&2
    exit 1
  fi
  echo "Creating local Python environment in $VENV..."
  "$PYTHON" -m venv "$VENV"
fi

if [[ ! -f "$STAMP" ]] || ! cmp -s requirements.txt "$STAMP"; then
  echo "Installing RRG dependencies..."
  "$VENV/bin/python" -m pip install -r requirements.txt
  cp requirements.txt "$STAMP"
fi

exec "$VENV/bin/python" vp_gui.py "$@"
