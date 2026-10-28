# Business Rules

Every rule has an ID. Analytics, validation and ground-truth labels reference these IDs so that
each flag is traceable to a documented rule.

## Bands
| ID | Rule |
|---|---|
| R-BAND-01 | A salary record must be compared to the band whose `effective_from ≤ month-start` and `effective_to ≥ month-end` for its (role, level, location). |
| R-BAND-02 | Bands for the same (role, level, location) must not overlap in time. |
| R-BAND-03 | `band_min < band_mid < band_max`; band currency equals location currency. |
| R-BAND-04 | Band midpoint = `market_base_usd × level_multiplier × geo_differential × yearly_market_index ÷ usd_per_unit(Jan of year)`. |

## Normalization
| ID | Rule |
|---|---|
| R-NORM-01 | `base_salary_fte = base_salary_actual / fte`. Comparisons always use FTE-normalized pay. |
| R-NORM-02 | Cross-currency comparisons use the FX rate for (currency, period_month). A missing rate makes the record **non-comparable** (excluded + flagged), never silently treated as 1.0. |

## Metrics
| ID | Rule |
|---|---|
| R-MET-01 | `compa_ratio = base_salary_fte / band_mid` (same currency as band). |
| R-MET-02 | `band_position = (base_salary_fte − band_min)/(band_max − band_min)`; < 0 = below band, > 1 = above band. |

## Comparable groups
| ID | Rule |
|---|---|
| R-GRP-01 | Default group = same role + level + location. Grouping across roles is allowed only within a job family with a non-empty `grouping_rationale`; cross-family groups require rationale **and** `grouping_basis = CROSS_FAMILY`. |
| R-GRP-02 | Groups with fewer than 5 members are not used for statistical outlier detection (reported as "insufficient n"). |

## Disparity detection
| ID | Rule |
|---|---|
| R-DIS-01 | Expected pay is modelled from documented factors only: level, location, role, tenure, performance rating, certifications, critical-skill flag. |
| R-DIS-02 | An **unexplained outlier** is a record whose log-residual vs. expected pay is beyond ±2.0 robust z (MAD) within its comparable group, after documented factors. |
| R-DIS-03 | Compa-ratio < 0.80 or band_position < 0 → `BELOW_BAND_MIN` review even if explained. |

## Adjustments & approvals
| ID | Rule |
|---|---|
| R-ADJ-01 | Every proposal links ≥ 1 evidence row (metric snapshot and/or performance evidence) and its comparable group. |
| R-ADJ-02 | Proposed salary must not exceed band_max; default target = group median compa-ratio, minimum band_min. |
| R-ADJ-03 | Allowed transitions and actors: SUBMITTED (HR_PARTNER), MANAGER_APPROVED (MANAGER of employee), HR_APPROVED (HR_PARTNER ≠ proposer), APPLIED (SYS_ADMIN), REJECTED (MANAGER or HR_PARTNER), WITHDRAWN (proposer). |
| R-ADJ-04 | A salary record with `change_reason = ADJUSTMENT` requires its proposal to have an `HR_APPROVED` event dated before the record's month. |
| R-ADJ-05 | Approval events are append-only; proposal status = latest event's `to_status`. |

## Generation-time rules (realism)
| ID | Rule |
|---|---|
| R-GEN-01 | Annual merit in March: 0–6% driven by performance rating. |
| R-GEN-02 | Promotion: +8–15% and level rank +1; eligible after ≥ 12 months at level and rating ≥ 4. |
| R-GEN-03 | Relocation changes location and currency; salary re-set to new band position (±0.1). |
| R-GEN-04 | FTE changes keep FTE-normalized pay constant (actual pay scales with FTE). |
