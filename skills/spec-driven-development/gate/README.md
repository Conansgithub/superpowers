# spec gate (portable engine)

Portable python3 port of due's Go spec-check. Static, stdlib-only, no install.
Enforcement lives at the verification/finishing seams — not in any project's CI.

## Run

```bash
python3 spec_check.py --lang go -invariants docs/migration/INVARIANTS.md -root .
```

Exit: `0` pass / `1` block (B1–B4 + coverage) / `2` usage or IO error.
`--lang` is required (no implicit default). `--skip a,b` prunes extra dirs.

## Test

```bash
bash run-test.sh   # unit tests + conformance corpus
```

## Add a language

One row in `specanchor/langs.py` (test-file suffix, pointer extension, behavior
declaration). Nothing else in the engine is language-aware.
