# 方法论注释两类标记约定 (Marker Convention)

Two distinct marker types handle methodology annotations. They are **never unified** — each has a separate lifecycle, parser, and export rule.

## Type 1 — Binding Tag: `// spec:INV-X`

| Property | Value |
|----------|-------|
| Form | `// spec:INV-LEDGER-1` (with optional ` anchor:<hex>`) |
| Scope | Test files only (gate scans `_test.go` / `_test.py` etc.) |
| Gate action | `_TAG_RE = re.compile(r"spec:(INV-[A-Z]+-\d+)…")` — the engine anchors the invariant to the test |
| Prefix constraint | Only `INV-` prefix is recognized; `spec:BAG-1` in a test is NOT a binding tag |
| Placement | Standalone comment line **or** embedded anywhere (e.g. `// 绑定 [[ref:INV-X]]: spec:INV-X`) |
| Export rule | **Strip whole line** matching `^\s*//.*\bspec:INV-` from the org snapshot |
| Change rule | **Never modify** — changing this breaks the invariant binding |

## Type 2 — Prose Reference: `[[ref:…]]`

| Property | Value |
|----------|-------|
| Form | `[[ref:INV-CAP-1 capacity ceiling]]` or `[[ref:BAG-10]]` |
| Scope | Any file: source comments, godoc, swagger `@Description`, SQL comments, markdown, YAML |
| Gate action | Ignored — `ref:` does not contain `spec:` substring, gate regex does not match |
| Content | Any methodology ID — invariants (`INV-`), module spec IDs (`BAG-10`), or free text |
| Export rule | **Strip the `[[ref:…]]` segment** (`\[\[ref:[^\]]*\]\]`) from the org snapshot |
| Change rule | Free to add, update, or remove — advisory only |

## Canonical examples

```go
// binding tag in test — wires INV-LEDGER-1 to this test function
// spec:INV-LEDGER-1

// prose reference in production source — documents design rationale
// 退款守恒([[ref:INV-LEDGER-1]]/[[ref:INV-RES-2]])：refundAllOps 退旧池独占技能

// prose reference to module spec ID (not an invariant)
// [[ref:BAG-10]] 列表逐项透出 6 个 can_* 字段

// combined: prose + binding on same function
// 绑定 [[ref:INV-NOTIFY-1]]: spec:INV-NOTIFY-1
func TestNotifierNonNil(t *testing.T) {
```

```sql
-- [[ref:INV-ESCROW-1]] escrow 守恒：锁定额 = Σ成交支付 + 返还残额
```

```yaml
# cockpit-api 永不允许出现在此([[ref:INV-DOCS-2]])
```

## Why two types (never unified)

The gate's `_TAG_RE` is a hard boundary — it only parses `spec:INV-` and feeds the anchor engine. Widening it to accept module IDs (`spec:BAG-1`) or prose references would cause every `[[spec:]]` wrapped mention in docs to register as an orphan (no matching invariant), breaking the gate for all projects using the same engine.

Keeping `[[ref:]]` separate means:

- The gate's binding count stays exact and auditable.
- Prose references can appear in production source, docs, YAML, SQL — places where binding tags must not appear.
- Export scrubber needs only two simple rules: strip binding lines + strip `[[ref:…]]` segments.

## Bare-refs audit

The `spec-check audit --audit-bare-refs` flag scans for methodology tokens that are neither wrapped in `[[ref:…]]` nor acting as binding tags (`spec:INV-`):

```bash
python3 gate/spec_check.py audit --audit-bare-refs -root .
```

Output is advisory (exit 0 always). Zero findings = the export scrubber's two rules are sufficient to remove all methodology footprint.

**Run this before any org snapshot export** to confirm zero bare tokens remain.
