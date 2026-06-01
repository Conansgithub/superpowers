#!/usr/bin/env bash
# check-weave.sh — structural lint for the spec-driven-development weave.
# Usage: check-weave.sh [ROOT]   (ROOT defaults to the repo root)
set -uo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
SKILL_DIR="$ROOT/skills/spec-driven-development"
SKILL_MD="$SKILL_DIR/SKILL.md"
REFS=(invariants-template manifest-template ears-sentences gate-contract)
SEAMS=(brainstorming writing-plans test-driven-development verification-before-completion finishing-a-development-branch)
PROCS=("Procedure 1 · Seed" "Procedure 2 · Annotate" "Procedure 3 · Bind" "Procedure 4 · Gate" "Procedure 5 · Reconcile")

fail=0
err() { echo "FAIL: $*"; fail=1; }

# C1
[ -f "$SKILL_MD" ] || err "C1 missing skill: skills/spec-driven-development/SKILL.md"

# C2
for r in "${REFS[@]}"; do
  [ -f "$SKILL_DIR/references/$r.md" ] || err "C2 missing reference: references/$r.md"
done

# C3
if [ -f "$SKILL_MD" ]; then
  for p in "${PROCS[@]}"; do
    grep -qF "$p" "$SKILL_MD" || err "C3 SKILL.md missing heading: $p"
  done
fi

# C4 + C5 (index-aligned seam → procedure)
for i in "${!SEAMS[@]}"; do
  s="${SEAMS[$i]}"; want="${PROCS[$i]}"; f="$ROOT/skills/$s/SKILL.md"
  if [ ! -f "$f" ]; then err "C4 missing upstream skill: skills/$s/SKILL.md"; continue; fi
  starts=$(grep -cF "spec-weave:start" "$f"); ends=$(grep -cF "spec-weave:end" "$f")
  if [ "$starts" != "1" ] || [ "$ends" != "1" ]; then
    err "C4 $s: want exactly one spec-weave pair (start=$starts end=$ends)"; continue
  fi
  # assumes one start-before-end pair on distinct lines (C4 above guarantees the count)
  block=$(sed -n '/spec-weave:start/,/spec-weave:end/p' "$f")
  if ! printf '%s\n' "$block" | grep -qF "$want"; then
    err "C5 $s: marker block must name '$want'"
  elif [ -f "$SKILL_MD" ] && ! grep -qF "$want" "$SKILL_MD"; then
    err "C5 $s: '$want' is not a heading in SKILL.md"
  fi
done

# Projection sanity (artifacts under skills/) is guaranteed by construction: this lint only ever inspects paths under $ROOT/skills/. A meaningful enforcement (e.g. "skill is git-tracked so it ships") is deferred.

if [ "$fail" = 0 ]; then echo "OK: spec-weave lint passed"; fi
exit "$fail"
