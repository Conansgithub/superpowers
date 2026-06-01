#!/usr/bin/env bash
# Entry point for the spec-weave structural lint.
# 1) runs the lint's own fixture tests; 2) runs the lint against this repo.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
echo "== fixture tests =="
bash "$HERE/test-check-weave.sh"
echo "== lint against repo =="
bash "$HERE/check-weave.sh"
