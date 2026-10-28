# Project Plan — Pay Equity Analyzer

Goal: an end-to-end, reproducible workflow that compares compensation against role,
level, location and documented job-related factors, flags **unexplained** disparities,
and produces auditable adjustment proposals — all on fully synthetic data.

The work is split into 10 parts. Each part has a clear deliverable and "done when"
check so we can build and verify incrementally.

| Part | Name | Main files | Done when |
|------|------|-----------|-----------|
| 0 | Scaffolding & design docs | `docs/*`, `README.md`, this file | Structure exists, data dictionary + ERD agreed |
| 1 | Config, IDs, master data | `config.py`, `ids.py`, `generators/master.py` | Roles, levels, role-levels (200), locations, FX rates, effective-dated bands generated deterministically |
| 2 | Workforce & job history | `generators/employees.py`, `generators/assignments.py` | 5,000 employees, assignment history incl. promotions, FTE changes, relocations (currency changes), managers/HR partners |
| 3 | Salary history & factors | `generators/salary.py`, `generators/performance.py`, `generators/tenure.py` | 36 months of salary records per active employee, performance evidence, tenure snapshots, promotions table |
| 4 | Analytics engine | `analytics/normalize.py`, `metrics.py`, `comparables.py`, `disparity.py` | Currency + FTE normalization, compa-ratio, band position, comparable groups, unexplained-residual outliers |
| 5 | Review workflow | `workflow/proposals.py`, `workflow/approvals.py` | Adjustment proposals with evidence links and append-only approval trail |
| 6 | Edge-case injection & ground truth | `anomalies/inject.py`, `anomalies/ground_truth.py` | 5 labelled anomaly types injected; `ground_truth.csv/json` written separately |
| 7 | Validation suite | `validation/checks.py`, `validation/report.py` | PK/FK, enums, date order, arithmetic reconciliation, lifecycle, duplicates → `validation_summary.json` |
| 8 | Export & documentation | `export/*` | CSV + JSON + SQL seed, manifest with checksums, README/data dictionary final |
| 9 | Reproducibility, tests, publish | `reproducibility.py`, `tests/*` | Two runs with seed 20261022 produce identical checksums; pytest green; pushed to public GitHub |

## Dependency order

```
Part 1 (master) ──► Part 2 (employees/assignments) ──► Part 3 (salary/perf/tenure)
                                                            │
                                   Part 6 (inject anomalies)◄┘
                                            │
                     Part 4 (analytics) ◄───┘
                            │
                     Part 5 (proposals/approvals)
                            │
             Part 7 (validation) ─► Part 8 (export) ─► Part 9 (repro + tests + push)
```

Anomalies (Part 6) are injected into the *baseline-valid* data before analytics runs, so the
analytics/validation layers must actually detect them. Ground truth is written to its own
folder and is never read by the analytics code.

## Key design decisions (Part 0)

1. **Synthetic only.** No external personal data. Public sources (if any) are cited for
   schema inspiration only — see `docs/provenance.md`.
2. **Single generator, parameterized scale.** `--scale starter` (500 employees) and
   `--scale full` (5,000 employees) use the same code path and seed.
3. **Append-only history.** Assignments, salary records, band versions and approval events
   are never overwritten; changes create new rows with effective dates.
4. **Derived ≠ generated.** Compa-ratio, band position, tenure, totals and statuses are
   calculated from source rows (Part 4 / Part 3), never randomly drawn.
5. **Ground truth from rules.** Labels come from documented rule IDs in
   `docs/business_rules.md`, not random assignment.
6. **Tooling.** Python 3.12, pandas + numpy, pytest. Plain CLI via `python -m payequity`.

## Current status

Parts 0–9 are implemented locally. The full test suite passes (28 tests), starter
generation is reproducible with seed `20261022`, and the CLI supports generation,
analysis, validation, reproducibility, and end-to-end export. Public repository
publication is complete at https://github.com/Abhishek0456/pay-equity-analyzer.
