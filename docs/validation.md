# Validation Checks (Part 7)

Output: `output/<scale>/reports/validation_summary.json` — one entry per check with
`check_id`, `table`, `status` (PASS/FAIL/WARN), `violations`, `sample_ids`.
Expected violations caused by injected anomalies are reported separately as
`expected_violations` (matched against ground truth) so the baseline must be 100% clean.

| Check ID | Category | Description |
|---|---|---|
| V-PK | Primary keys | Unique, non-null PK in every table |
| V-FK | Foreign keys | Every FK resolves to an existing parent row |
| V-ENUM | Allowed values | Enum columns contain only documented values |
| V-FMT | ID format | IDs match regex conventions (EMP-000001, BAND-…-2026, SAL-…-YYYY-MM, ADJ-2026-000001) |
| V-DATE | Date ordering | hire ≤ termination; effective_from ≤ effective_to; events increasing |
| V-OVERLAP | Effective dating | No overlapping assignments per employee / bands per key |
| V-RECON | Arithmetic | Derived metrics recompute exactly from source (FTE, FX, compa-ratio, band position, increase_pct) |
| V-LIFE | Lifecycle | Approval transitions valid and by permitted actor; status = last event |
| V-DUP | Duplicates | No duplicate (employee, month) salary rows; no duplicate group members |
| V-BAND | Band rule | Each salary record's band is effective for its month (R-BAND-01) |
| V-GT | Leakage | No ground-truth column appears in any input table |
