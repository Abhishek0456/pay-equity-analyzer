# Pay Equity Analyzer

Compare compensation against **role, level, location and documented job-related factors** to
identify **unexplained disparities**, then produce auditable adjustment proposals with an
approval trail. All data is synthetic and reproducible from a fixed seed.

> Status: **Part 0 — scaffolding.** See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the 10-part build plan.

## Workflow

1. Generate master data: Role, Level, RoleLevel (200 combos), Location, FX rates, CompensationBand (effective-dated per year).
2. Generate dependent records: Employee, JobAssignment history, SalaryRecord (36 months), PerformanceEvidence, Tenure, Promotion.
3. Inject labelled edge cases → `ground_truth/` (kept separate from inputs).
4. Analyze: normalize FTE + currency, compute compa-ratio and band position, build comparable groups, detect unexplained outliers.
5. Review: create AdjustmentProposals with evidence and an append-only approval trail.
6. Validate (PK/FK/enums/dates/reconciliation/lifecycle/duplicates) and export CSV / JSON / SQL + manifest.
7. Regenerate with the same seed and compare checksums.

## Project structure

```
pay-equity-analyzer/
├── config/
│   ├── default.json            # seed, scales, history window, anomaly rates, thresholds
│   └── reference/              # roles, levels, locations, FX anchors (illustrative, synthetic)
├── docs/
│   ├── data_dictionary.md      # every table/field: type, required, allowed values, units, keys
│   ├── erd.md                  # ER diagram, cardinality, lifecycle states
│   ├── business_rules.md       # rule IDs used by analytics, validation and ground truth
│   ├── edge_cases.md           # injected negative scenarios + expected decisions
│   ├── validation.md           # validation check catalogue
│   └── provenance.md           # lawful-use / source manifest
├── src/payequity/
│   ├── cli.py, pipeline.py     # entry point + orchestration
│   ├── config.py, ids.py, rng.py
│   ├── generators/             # master, employees, assignments, salary, performance, tenure, promotions
│   ├── anomalies/              # edge-case injection + ground truth writer
│   ├── analytics/              # normalize, bands, metrics, comparables, disparity, evaluation
│   ├── workflow/               # adjustment proposals + approval state machine
│   ├── validation/             # schema, checks, report
│   ├── export/                 # CSV/JSON writers, SQL seed, manifest
│   └── reproducibility.py
├── tests/                      # pytest suite
├── scripts/                    # run_all.sh / run_all.ps1
├── samples/                    # committed starter-scale sample output
└── output/                     # generated data (git-ignored)
```

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Running (available once Parts 1–9 are implemented)

```bash
python -m payequity all --scale starter        # 500 employees
python -m payequity all --scale full           # 5,000 employees
python -m payequity reproduce --scale starter  # two runs, compare checksums
```

Default seed: `20261022` (override with `--seed`).

Additional commands: `analyze` writes analytics tables; `validate` writes a validation report.

Output layout per scale:
```
output/<scale>/
├── data/          csv/ json/ sql/       # input tables (no labels)
├── analysis/      compensation_metrics, comparable groups, outliers, proposals, approval_event
├── ground_truth/  ground_truth.csv / .json
└── reports/       validation_summary.json, evaluation.json, manifest.json
```

## Data provenance

Fully synthetic; no personal data. See [docs/provenance.md](docs/provenance.md).
