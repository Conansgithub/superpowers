# spec gate (portable engine)

Portable python3 port of due's Go spec-check. Static, stdlib-only, no install.
Enforcement lives at the verification/finishing seams — not in any project's CI.

## Run

```bash
# Explicit flags (legacy / no descriptor):
python3 spec_check.py --lang go -invariants docs/migration/INVARIANTS.md -root .

# Or declare config once in <root>/.spec-check.json, then:
python3 spec_check.py -root .                  # check, reads .spec-check.json
python3 spec_check.py adopt -root .            # detect lang/paths, write .spec-check.json
python3 spec_check.py init -root . --lang go   # scaffold a greenfield project
```

Exit: `0` pass / `1` block (B1–B4 + coverage) / `2` usage or IO error.
Precedence: explicit flag > `.spec-check.json` > built-in default. `--lang` is
required unless the descriptor supplies it. `--skip a,b` prunes extra dirs.
Descriptor `exclude_globs` prunes root-relative generated or vendored artifacts
from tag scan and bare-ref audit, for example:

```json
{
  "exclude_globs": [
    "cmd/*/docs/**",
    "cmd/cockpit-api/dist/**",
    "internal/docsportal/assets/**"
  ]
}
```

`--resolver <cmd>` swaps coverage binding resolution out to an external command
(non-code domains): it receives `test <file> <fn>` or `artifact <path>` as argv,
exit 0 = resolved.

## Test

```bash
bash run-test.sh   # unit tests + conformance corpus
```

## Add a language

One row in `specanchor/langs.py` (test-file suffix, pointer extension, behavior
declaration). Nothing else in the engine is language-aware.
