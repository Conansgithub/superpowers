---
name: spec-driven-development
description: Use at the five workflow seams (brainstorm, plan, TDD, verification, finishing) to keep specs anchored to code — surface invariants, annotate plans with spec IDs, bind rules to tests/contracts, run the gate, and reconcile from reality. Project-agnostic; the gate engine ships with this skill and runs against the target project.
---

# Spec-Driven Development

Keep specs from drifting from code. Every rule lives in the least-rot-prone form for its kind, and a gate fails when a rule and its proof come unlinked.

Three kinds of rule, three drift-resistant homes:
- **invariant** (always true) → a line in `INVARIANTS.md` + a property test + a `// spec:ID` tag + a fingerprint check.
- **behavior** (one scenario) → one given/when/then test; the sentence and the test are the same artifact (no tag).
- **contract** (interface shape) → a generated file (e.g. OpenAPI), regenerated and diffed; never tagged.

Full format in `references/`: `invariants-template.md`, `manifest-template.md`, `ears-sentences.md`, `gate-contract.md`.

This skill is woven into five upstream skills; each runs one procedure below at its seam.

## Procedure 1 · Seed
**Seam:** end of `brainstorming`, once the design is settled.
Extract rules the design establishes that must ALWAYS hold (invariants, not behaviors). Append each to `INVARIANTS.md` with `Status: stated` and `Since: <date>`. Capture, don't author — never invent invariants the design didn't establish.

## Procedure 2 · Annotate
**Seam:** `writing-plans`, in Task Structure.
Tag each plan task with the spec IDs it touches (`INV-*` for invariants, `<module>-*` for module rules). Register any new rule the plan introduces in its module manifest with `Status: stated`.

## Procedure 3 · Bind
**Seam:** `test-driven-development`, when writing assertions.
- invariant: put a `// spec:INV-*` comment on the guarding assertion (prefer a property test — one that checks ALL cases, e.g. Go `testing/quick` or `rapid`).
- behavior: write the rule as a given/when/then comment directly above the table-driven test that runs it. No tag — the sentence and the test are one artifact.
- contract: don't hand-write assertions; the generated file + diff is the binding.

## Procedure 4 · Gate
**Seam:** `verification-before-completion`.
Run the gate engine shipped with this skill against the project (B1–B4 + coverage), plus contracts-check. Red = not done; fix before any completion claim. The engine is at `gate/spec_check.py` (stdlib python3, honors `references/gate-contract.md`); point it at the project:

    python3 "$SKILL_DIR/gate/spec_check.py" -invariants <INVARIANTS path> -root <root> --lang <go|python|…> [--skip <dirs>]

`$SKILL_DIR` is this skill's own directory. Supply the project's invariants path, language, and any extra skips — e.g. a Go project whose baseline lives at `docs/migration/INVARIANTS.md`: `-invariants docs/migration/INVARIANTS.md -root . --lang go`. The formal per-project descriptor (auto-detected paths/lang) is future work; for now pass the flags explicitly. **Enforcement lives here at the seam, not in CI.**

## Procedure 5 · Reconcile
**Seam:** start of `finishing-a-development-branch`, before merge/PR.
Read the ACTUAL slice diff + tests (never the plan). For each touched rule: if a green test now guards it, add the tag and flip `stated → enforced`. Add rules the slice revealed. If shipped code contradicts a rule, set `Status: violated` and STOP (release blocker). Update `Guarded by:`, `Since:`, and fingerprints. Re-run the gate (Procedure 4); it must be green before merge.

## Integration
Invoked at five seams, each via a `spec-weave` pointer block in the host skill:
- `superpowers:brainstorming` → Procedure 1 · Seed
- `superpowers:writing-plans` → Procedure 2 · Annotate
- `superpowers:test-driven-development` → Procedure 3 · Bind
- `superpowers:verification-before-completion` → Procedure 4 · Gate
- `superpowers:finishing-a-development-branch` → Procedure 5 · Reconcile

The gate runs at the verification and finishing seams, never in a project's CI.
