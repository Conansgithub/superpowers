#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
echo "== unit tests =="
( cd "$HERE" && python3 -m unittest discover -s tests -t . -p 'test_*.py' )
echo "== conformance =="
python3 "$HERE/conformance/run_conformance.py"
echo "OK: spec-gate suite passed"
