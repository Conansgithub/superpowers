# EARS sentences

Write every rule as one of four fixed shapes. The shapes keep a single sentence unambiguous and testable; cross-rule consistency is the gate's job, not the sentence's.

- **Unconditional:** `… SHALL …` (invariants and contracts)
- **When:** `当 … 时，… SHALL …` (event-driven behavior)
- **If:** `若 …，则 … SHALL …` (error / unwanted condition)
- **Where (toggle):** `凡启用 … 处，… SHALL …` (optional features)
- `在 … 期间 …` (state-driven) is allowed but rare.

Rules:
- Use `SHALL` / `SHALL NOT` only — never "should" / "may". Optionality is `凡启用…处`, not "may".
- Max 3 preconditions per sentence; beyond that, reference a decision table — never cram conditions into the sentence.
