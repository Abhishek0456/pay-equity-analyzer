"""Part 5 — Create adjustment proposals with evidence links (R-ADJ-01/02)."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from payequity.ids import adjustment_id


def create_proposals(
    candidates: pd.DataFrame,
    year: int,
    proposed_by: str,
    evidence: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Create capped proposal and evidence-bridge rows from flagged candidates."""
    required = {"employee_id", "salary_record_id", "group_id", "base_salary_fte", "band_max"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"candidates missing required columns: {sorted(missing)}")
    if evidence is not None and evidence.empty:
        raise ValueError("each proposal requires at least one evidence row")
    proposals, links = [], []
    for n, (_, row) in enumerate(candidates.iterrows(), 1):
        current = float(row["base_salary_fte"])
        target = min(float(row["band_max"]), max(current, float(row.get("target_salary_fte", current))))
        if target <= current:
            continue
        aid = adjustment_id(year, n)
        proposals.append({"adjustment_id": aid, "employee_id": row["employee_id"],
                          "basis_salary_record_id": row["salary_record_id"],
                          "group_id": row["group_id"], "current_salary_fte": current,
                          "proposed_salary_fte": target, "increase_pct": target / current - 1,
                          "reason_code": row.get("reason_code", "UNEXPLAINED_GAP"),
                          "status": "DRAFT", "proposed_by": proposed_by,
                          "created_at": datetime.now(timezone.utc).isoformat(),
                          "effective_month": row.get("period_month")})
        if evidence is not None:
            evidence_rows = evidence
            if "salary_record_id" in evidence and "salary_record_id" in row:
                evidence_rows = evidence[evidence["salary_record_id"].eq(row["salary_record_id"])]
            for eid in evidence_rows.get("evidence_id", evidence_rows.index):
                links.append({"adjustment_id": aid, "evidence_id": eid,
                              "evidence_role": "SUPPORTING"})
    return {"adjustment_proposal": pd.DataFrame(proposals),
            "proposal_evidence": pd.DataFrame(links)}


def build_proposals(*args, **kwargs):
    return create_proposals(*args, **kwargs)
