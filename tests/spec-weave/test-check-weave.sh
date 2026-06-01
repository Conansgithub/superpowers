#!/usr/bin/env bash
# Tests for check-weave.sh — builds temp skill trees and asserts the lint verdict.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LINT="$HERE/check-weave.sh"
fails=0
note() { printf '  [%s] %s\n' "$1" "$2"; }

# Build a PASSING tree at $1
make_good() {
  local root="$1" s
  mkdir -p "$root/skills/spec-driven-development/references"
  {
    echo "## Procedure 1 · Seed";      echo "## Procedure 2 · Annotate"
    echo "## Procedure 3 · Bind";      echo "## Procedure 4 · Gate"
    echo "## Procedure 5 · Reconcile"
  } > "$root/skills/spec-driven-development/SKILL.md"
  for r in invariants-template manifest-template ears-sentences gate-contract; do
    echo "x" > "$root/skills/spec-driven-development/references/$r.md"
  done
  # index-aligned seam → procedure
  local seams=(brainstorming writing-plans test-driven-development verification-before-completion finishing-a-development-branch)
  local procs=("Procedure 1 · Seed" "Procedure 2 · Annotate" "Procedure 3 · Bind" "Procedure 4 · Gate" "Procedure 5 · Reconcile")
  local i
  for i in "${!seams[@]}"; do
    mkdir -p "$root/skills/${seams[$i]}"
    {
      echo "# host skill"
      echo "<!-- spec-weave:start -->"
      echo "> run ${procs[$i]} here."
      echo "<!-- spec-weave:end -->"
    } > "$root/skills/${seams[$i]}/SKILL.md"
  done
}

assert_exit() { # $1=desc $2=expected(0|nonzero) $3=root
  bash "$LINT" "$3" >/dev/null 2>&1; local rc=$?
  if { [ "$2" = 0 ] && [ "$rc" = 0 ]; } || { [ "$2" != 0 ] && [ "$rc" != 0 ]; }; then
    note PASS "$1"; else note FAIL "$1 (rc=$rc want $2)"; fails=$((fails+1)); fi
}

assert_msg() { # $1=desc $2=expected-substring $3=root
  local out rc
  out=$(bash "$LINT" "$3" 2>&1); rc=$?
  if [ "$rc" != 0 ] && printf '%s\n' "$out" | grep -qF "$2"; then
    note PASS "$1"; else note FAIL "$1 (rc=$rc, want msg '$2')"; fails=$((fails+1)); fi
}

G=$(mktemp -d); make_good "$G"
assert_exit "good tree passes" 0 "$G"

B1=$(mktemp -d); make_good "$B1"; rm "$B1/skills/spec-driven-development/SKILL.md"
assert_msg "C1 missing SKILL.md fails" "C1 missing skill" "$B1"

B2=$(mktemp -d); make_good "$B2"; rm "$B2/skills/spec-driven-development/references/gate-contract.md"
assert_msg "C2 missing reference fails" "C2 missing reference" "$B2"

B3=$(mktemp -d); make_good "$B3"
# drop one procedure heading
grep -v "Procedure 4 · Gate" "$B3/skills/spec-driven-development/SKILL.md" > "$B3/tmp" && mv "$B3/tmp" "$B3/skills/spec-driven-development/SKILL.md"
assert_msg "C3 missing procedure heading fails" "C3 SKILL.md missing heading" "$B3"

B4=$(mktemp -d); make_good "$B4"
# duplicate a start marker → unbalanced
printf '<!-- spec-weave:start -->\n' >> "$B4/skills/brainstorming/SKILL.md"
assert_msg "C4 unbalanced markers fails" "want exactly one spec-weave pair" "$B4"

B5=$(mktemp -d); make_good "$B5"
# block names a procedure not matching this seam
sed 's/Procedure 2 · Annotate/Procedure 9 · Bogus/' "$B5/skills/writing-plans/SKILL.md" > "$B5/tmp" && mv "$B5/tmp" "$B5/skills/writing-plans/SKILL.md"
assert_msg "C5 wrong procedure name fails" "marker block must name" "$B5"

B6=$(mktemp -d); make_good "$B6"
# procedure names present only as body text (Integration-style), not as ## headings → C3 must still fire
printf '## Procedures\n- superpowers:brainstorming → Procedure 1 · Seed\n- Procedure 2 · Annotate\n- Procedure 3 · Bind\n- Procedure 4 · Gate\n- Procedure 5 · Reconcile\n' > "$B6/skills/spec-driven-development/SKILL.md"
assert_msg "C3 requires real headings not just name mentions" "C3 SKILL.md missing heading" "$B6"

rm -rf "$G" "$B1" "$B2" "$B3" "$B4" "$B5" "$B6"
if [ "$fails" = 0 ]; then echo "ALL PASS"; exit 0; else echo "$fails FAILED"; exit 1; fi
