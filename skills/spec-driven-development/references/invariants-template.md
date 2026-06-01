# INVARIANTS.md — entry template

Global, cross-module rules that must ALWAYS hold. One entry each:

```
### INV-<DOMAIN>-<n> — <one-line name>
Holds:      <the always-true rule, as one unconditional SHALL sentence>
Why:        <the class of bug it prevents — the part code can't express>
Guarded by: <test file> (spec:INV-<DOMAIN>-<n>)
Anchor:     sha-<fingerprint of the Holds: text at last calibration>   # for B4
Status:     stated | enforced | violated
Since:      <date / slice>
```

- `Holds:` uses one EARS sentence, `SHALL` only (see `ears-sentences.md`).
- `Anchor:` is the text fingerprint the gate's B4 check compares against.
- Numbers are permanent: never renumber, never reuse on rename.
