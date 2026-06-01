# Gate contract

Two commands at the verification/finishing seams. Static and fast. Not in any project's CI.

## spec-check (static)
Reads `INVARIANTS.md` and the module manifests; greps test code for `spec:` tags. Never runs tests.
- **B1 coverage:** every `enforced` invariant has ≥1 tag.
- **B2 no orphan:** every `spec:` tag points to a real invariant.
- **B3 no violation:** no invariant is `violated`.
- **B4 fingerprint:** an invariant's `Holds:` text changed since last calibration (fingerprint ≠ `Anchor:`) → SUSPECT. Advisory by default; a strict flag makes it block.
- **coverage:** every `enforced` manifest rule binds to something real (invariant→tag, behavior→`file::Func`, contract→`生成: path` artifact exists). Unbound-enforced = blocking; `stated` is advisory.

Exit codes: `0` pass / `1` block (B1–B4 + coverage) / `2` usage or IO error.

## Engine + resolver (how the gate stays language/domain-agnostic)
The engine is universal — read spec text, hash it, grep `spec:ID`, check files exist. What varies is the **resolver** that answers "does this binding resolve?":
- **tag** binding → grep the token (universal).
- **artifact** binding → the `生成: path` file exists (universal).
- **verified-behavior** binding → default: a test function `file::Func` exists (swap one regex per language: Go `func X(`, Python `def x`). Non-code domains: a `--resolver` hook answers it (a checklist item, a sign-off).

The single source of truth is this contract plus a shared conformance fixture set — not any one binary. Multiple implementations (e.g. a Go gate and a portable python3 gate) are fine as long as both pass the fixtures.

## contracts-check (separate, per-project)
Not static: regenerates the interface file (e.g. `api/openapi.json`) and fails on drift (`oasdiff` + `git diff --exit-code`). Per-project because it runs the project's generator. `spec-check` only verifies a contract rule is wired to `contracts-check`; the real diff runs here.
