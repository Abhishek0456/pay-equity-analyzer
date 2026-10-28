# Data Dictionary (draft v0.1 — Part 0)

Conventions
- Types: `str`, `int`, `decimal(p,s)`, `date` (ISO `YYYY-MM-DD`), `month` (`YYYY-MM`), `datetime` (ISO 8601 UTC), `bool`.
- Money is stored in **local currency, annual, gross base salary** unless the column name says `_usd` or `_fte`.
- `Req` = required (Y) / optional (N). `PK` = primary key, `FK` = foreign key, `U` = unique.
- All IDs are immutable once generated and zero-padded.

---

## Master data

### role  (`role.csv`)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| role_id | str | Y | `ROLE-<CODE>` e.g. `ROLE-SWE` | PK | matches `^ROLE-[A-Z]{3}$` |
| role_code | str | Y | 3 upper letters | U | |
| role_name | str | Y | free text | U | non-empty |
| job_family | str | Y | ENGINEERING, DATA, PRODUCT, SALES, MARKETING, FINANCE, HR, OPERATIONS, SUPPORT, LEGAL | | enum |
| market_base_usd | decimal(12,2) | Y | USD, annual, L1 FTE midpoint | | > 0 |
| is_active | bool | Y | true/false | | |

### level  (`level.csv`)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| level_id | str | Y | `L1`…`L8` | PK | |
| level_name | str | Y | Associate … Director | U | |
| track | str | Y | IC, MANAGEMENT | | enum |
| rank | int | Y | 1–8 | U | ascending with seniority |
| level_multiplier | decimal(5,3) | Y | ratio vs L1 | | ≥ 1.0, monotonic in rank |

### role_level  (`role_level.csv`) — bridge Role N:M Level (200 valid combinations)
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| role_level_id | str | Y | `RL-<ROLE>-<LEVEL>` | PK | |
| role_id | str | Y | | FK→role | |
| level_id | str | Y | | FK→level | (role_id, level_id) unique |

### location  (`location.csv`)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| location_id | str | Y | `LOC-<CODE>` e.g. `LOC-NYC` | PK | |
| city | str | Y | | | |
| country_code | str | Y | ISO 3166-1 alpha-2 | | |
| currency_code | str | Y | ISO 4217: USD, GBP, EUR, CAD, INR, SGD, AUD | | enum |
| geo_tier | int | Y | 1–3 | | |
| geo_differential | decimal(5,3) | Y | ratio vs US national (USD terms) | | > 0 |

### fx_rate  (`fx_rate.csv`)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| fx_rate_id | str | Y | `FX-<CCY>-<YYYY-MM>` | PK | |
| currency_code | str | Y | ISO 4217 | | enum |
| period_month | month | Y | | | (currency, month) unique |
| usd_per_unit | decimal(12,6) | Y | USD per 1 unit local | | > 0; USD = 1.0 |
| source | str | Y | `SYNTHETIC` | | |

### compensation_band  (`compensation_band.csv`)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| band_id | str | Y | `BAND-<ROLE>-<LEVEL>-<LOC>-<YYYY>` e.g. `BAND-SWE-L3-NYC-2026` | PK | |
| role_id | str | Y | | FK→role | |
| level_id | str | Y | | FK→level | (role, level) ∈ role_level |
| location_id | str | Y | | FK→location | |
| currency_code | str | Y | = location currency | | consistency check |
| band_min | decimal(12,2) | Y | local, annual, FTE 1.0 | | > 0 |
| band_mid | decimal(12,2) | Y | | | min < mid < max |
| band_max | decimal(12,2) | Y | | | spread (max/min) 1.3–1.8 |
| effective_from | date | Y | | | |
| effective_to | date | Y | | | effective_from ≤ effective_to; no overlap per (role, level, loc) |
| band_status | str | Y | ACTIVE, EXPIRED, FUTURE | | derived from as-of date |
| version | int | Y | 1..n | | |

---

## People & job history

### employee  (`employee.csv`)
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| employee_id | str | Y | `EMP-000001` | PK | `^EMP-\d{6}$` |
| display_name | str | Y | synthetic pseudonym (e.g. `Employee 000001`) | | no real names |
| hire_date | date | Y | | | ≤ termination_date |
| termination_date | date | N | | | |
| employment_status | str | Y | ACTIVE, ON_LEAVE, TERMINATED | | TERMINATED ⇔ termination_date set |
| manager_id | str | N | | FK→employee (self) | no self-reference, no cycles |
| hr_partner_id | str | N | | FK→employee | partner role = HRB |
| system_role | str | Y | EMPLOYEE, MANAGER, HR_PARTNER, SYS_ADMIN | | enum |
| analysis_cohort | str | N | COHORT_A, COHORT_B | | synthetic audit-only attribute; **never** used to set pay |

### job_assignment  (`job_assignment.csv`) — effective-dated history (Employee 1:N)
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| assignment_id | str | Y | `ASG-<EMP>-<NN>` | PK | |
| employee_id | str | Y | | FK→employee | |
| role_id | str | Y | | FK→role | |
| level_id | str | Y | | FK→level | (role, level) ∈ role_level |
| location_id | str | Y | | FK→location | |
| fte | decimal(3,2) | Y | 0.20–1.00 | | |
| effective_from | date | Y | | | ≥ hire_date |
| effective_to | date | N | null = current | | no overlaps per employee; contiguous |
| change_reason | str | Y | HIRE, PROMOTION, TRANSFER, RELOCATION, FTE_CHANGE | | enum |

### promotion  (`promotion.csv`) — Employee 1:N
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| promotion_id | str | Y | `PRM-000001` | PK | |
| employee_id | str | Y | | FK→employee | |
| from_assignment_id | str | Y | | FK→job_assignment | |
| to_assignment_id | str | Y | | FK→job_assignment | to.rank = from.rank + 1 |
| from_level_id / to_level_id | str | Y | | FK→level | |
| effective_date | date | Y | | | = to_assignment.effective_from |
| approved_by | str | Y | | FK→employee | MANAGER |

### tenure  (`tenure.csv`) — **derived** yearly snapshot (Employee 1:N)
| Field | Type | Req | Units | Key | Validation |
|---|---|---|---|---|---|
| tenure_id | str | Y | `TEN-<EMP>-<YYYY>` | PK | |
| employee_id | str | Y | | FK→employee | |
| as_of_date | date | Y | year end | | |
| company_tenure_years | decimal(5,2) | Y | years | | = (as_of − hire_date)/365.25 |
| role_tenure_years | decimal(5,2) | Y | years | | ≤ company tenure |
| level_tenure_years | decimal(5,2) | Y | years | | ≤ role tenure |

### performance_evidence  (`performance_evidence.csv`) — Employee 1:N
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| evidence_id | str | Y | `PERF-000001` | PK | |
| employee_id | str | Y | | FK→employee | |
| evidence_type | str | Y | ANNUAL_RATING, CERTIFICATION, CRITICAL_SKILL, MARKET_PREMIUM | | enum |
| review_year | int | Y | 2024–2026 | | |
| rating | int | N | 1–5 (required if ANNUAL_RATING) | | |
| value_text | str | N | e.g. certification name | | |
| documented_by | str | Y | | FK→employee | MANAGER or HR_PARTNER |
| documented_date | date | Y | | | within review_year+1 Q1 |

---

## Compensation transactions

### salary_record  (`salary_record.csv`) — monthly snapshot (Employee 1:N, Assignment 1:N)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| salary_record_id | str | Y | `SAL-<EMP>-<YYYY>-<MM>` e.g. `SAL-EMP-000001-2026-01` | PK | |
| employee_id | str | Y | | FK→employee | |
| assignment_id | str | Y | | FK→job_assignment | assignment active in month |
| band_id | str | Y | band used for comparison | FK→compensation_band | must be effective in month (rule R-BAND-01) |
| period_month | month | Y | 2024-01 … 2026-12 | | (employee, month) unique |
| currency_code | str | Y | ISO 4217 | | = location currency |
| base_salary_actual | decimal(12,2) | Y | local, annual, at actual FTE | | > 0 |
| fte | decimal(3,2) | Y | 0.20–1.00 | | = assignment.fte |
| change_reason | str | Y | NONE, HIRE, MERIT, PROMOTION, TRANSFER, RELOCATION, FTE_CHANGE, ADJUSTMENT | | enum |
| adjustment_id | str | N | | FK→adjustment_proposal | required when change_reason = ADJUSTMENT |

Derived (written by analytics to `compensation_metrics.csv`, not stored in source):
`base_salary_fte = base_salary_actual / fte`, `base_salary_usd_fte = base_salary_fte × usd_per_unit`,
`compa_ratio = base_salary_fte / band_mid`, `band_position = (base_salary_fte − band_min)/(band_max − band_min)`.

---

## Analysis & review

### comparable_group  (`comparable_group.csv`)
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| group_id | str | Y | `CG-2026-0001` | PK | |
| level_id | str | Y | | FK→level | |
| location_id | str | N | null when grouped by geo_tier | FK→location | |
| geo_tier | int | N | 1–3 | | |
| grouping_basis | str | Y | SAME_ROLE, SAME_FAMILY, CROSS_FAMILY | | |
| grouping_rationale | str | N | required unless SAME_ROLE | | rule R-GRP-01 |
| as_of_month | month | Y | | | |

### comparable_group_role  — bridge ComparableGroup N:M Role
`group_id` FK, `role_id` FK; PK (group_id, role_id).

### comparable_group_member  — bridge ComparableGroup N:M Employee
`group_id` FK, `employee_id` FK, `salary_record_id` FK; PK (group_id, employee_id).

### adjustment_proposal  (`adjustment_proposal.csv`)
| Field | Type | Req | Allowed values / units | Key | Validation |
|---|---|---|---|---|---|
| adjustment_id | str | Y | `ADJ-2026-000001` | PK | |
| employee_id | str | Y | | FK→employee | |
| basis_salary_record_id | str | Y | | FK→salary_record | |
| group_id | str | Y | | FK→comparable_group | |
| current_salary_fte | decimal(12,2) | Y | local | | = metrics value |
| proposed_salary_fte | decimal(12,2) | Y | local | | > current; ≤ band_max |
| increase_pct | decimal(6,4) | Y | ratio | | = proposed/current − 1 |
| reason_code | str | Y | BELOW_BAND_MIN, UNEXPLAINED_GAP, COMPRESSION, PROMOTION_CATCHUP | | |
| status | str | Y | DRAFT, SUBMITTED, MANAGER_APPROVED, HR_APPROVED, APPLIED, REJECTED, WITHDRAWN | | = latest approval_event.to_status |
| proposed_by | str | Y | | FK→employee | HR_PARTNER |
| created_at | datetime | Y | | | |
| effective_month | month | N | set when APPLIED | | |

### proposal_evidence — bridge AdjustmentProposal N:M PerformanceEvidence
`adjustment_id` FK, `evidence_id` FK, `evidence_role` (SUPPORTING / CONTEXT); PK (adjustment_id, evidence_id).

### approval_event  (`approval_event.csv`) — append-only (Proposal 1:N)
| Field | Type | Req | Allowed values | Key | Validation |
|---|---|---|---|---|---|
| event_id | str | Y | `APR-2026-000001` | PK | |
| adjustment_id | str | Y | | FK→adjustment_proposal | |
| from_status | str | N | null for creation | | valid transition (see business_rules.md) |
| to_status | str | Y | proposal status enum | | |
| actor_id | str | Y | | FK→employee | actor role permitted for transition |
| actor_role | str | Y | MANAGER, HR_PARTNER, SYS_ADMIN | | |
| event_ts | datetime | Y | | | strictly increasing per proposal |
| comment | str | N | | | |

---

## Ground truth (separate folder, never an input)

### ground_truth  (`ground_truth/ground_truth.csv` + `.json`)
| Field | Type | Req | Allowed values |
|---|---|---|---|
| gt_id | str | Y | `GT-000001` |
| entity | str | Y | table name |
| record_id | str | Y | PK of affected row |
| issue_type | str | Y | EXPIRED_BAND, FTE_IGNORED, FX_MISSING, UNAPPROVED_ADJUSTMENT, INCOMPARABLE_GROUP, UNEXPLAINED_OUTLIER |
| rule_id | str | Y | rule from business_rules.md |
| expected_decision | str | Y | FLAG, EXCLUDE, REVIEW, PROPOSE_ADJUSTMENT |
| notes | str | N | |
