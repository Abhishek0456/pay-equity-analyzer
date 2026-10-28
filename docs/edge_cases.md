# Edge Cases & Negative Scenarios

Baseline data is generated valid first; edge cases are then injected into a **small, labelled
subset** of rows (default ~1–2% each, configurable). Each injection writes a ground-truth row with
`issue_type`, `rule_id` and `expected_decision`. Unrelated rows are never touched.

| issue_type | How it is injected | Rule broken | Expected detection / decision |
|---|---|---|---|
| EXPIRED_BAND | `salary_record.band_id` repointed to the previous year's band for that (role, level, location) | R-BAND-01 | Validation flags; analytics re-resolves the correct band → FLAG |
| FTE_IGNORED | Part-time employee's `base_salary_actual` written as the FTE salary while `fte < 1` (i.e. pay looks low vs. peers when not normalized — or the record is marked normalized twice) | R-NORM-01 | Metrics detect implausible compa-ratio jump at FTE change → FLAG |
| FX_MISSING | `fx_rate` row removed for one (currency, month), affecting all records in that slice | R-NORM-02 | Records excluded from cross-currency comparison → EXCLUDE + FLAG |
| UNAPPROVED_ADJUSTMENT | Salary record with `change_reason = ADJUSTMENT` whose proposal lacks `HR_APPROVED` (stopped at SUBMITTED / MANAGER_APPROVED) | R-ADJ-04 | Audit check → FLAG |
| INCOMPARABLE_GROUP | Comparable group mixing roles from different job families with empty `grouping_rationale` | R-GRP-01 | Group rejected for analysis → FLAG |
| UNEXPLAINED_OUTLIER | Employee's pay shifted −12% to −25% (or +20%) with **no** supporting factor change | R-DIS-02 | Disparity engine flags → PROPOSE_ADJUSTMENT / REVIEW |

Boundary coverage also generated in baseline (not anomalies): salary exactly at band_min/max,
FTE = 0.2 and 1.0, hire on first/last day of month, promotion in same month as merit,
relocation mid-year, terminated employees with partial history, groups with n < 5.

Evaluation: compare detected flags vs. `ground_truth` → precision, recall, F1 per issue_type
(written to `output/<scale>/reports/evaluation.json`).
