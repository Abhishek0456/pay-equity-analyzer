"""Generation orchestration shared by the CLI and tests."""

from __future__ import annotations

import pandas as pd

from payequity.config import load_settings
from payequity.generators.assignments import build_assignments
from payequity.generators.employees import build_employees
from payequity.generators.master import build_master
from payequity.generators.performance import build_performance
from payequity.generators.promotions import build_promotions
from payequity.generators.salary import build_salary
from payequity.generators.tenure import build_tenure
from payequity.rng import RngFactory
from payequity.analytics.normalize import normalize_salary
from payequity.analytics.metrics import calculate_metrics
from payequity.analytics.comparables import build_comparable_groups
from payequity.analytics.disparity import detect_disparities
from payequity.workflow.proposals import create_proposals
from payequity.workflow.approvals import append_approval_event
from payequity.anomalies.inject import inject_anomalies
from payequity.anomalies.ground_truth import write_ground_truth
from payequity.validation.checks import validate_tables
from payequity.validation.schema import validate_schema
from payequity.export.writers import write_tables
from payequity.export.sql import write_sql
from payequity.export.manifest import write_manifest


def generate(scale: str = "starter", seed: int | None = None) -> dict[str, pd.DataFrame]:
    """Generate all baseline source tables in dependency order."""
    settings = load_settings(scale=scale, seed=seed)
    rngs = RngFactory(settings.seed)
    master = build_master(settings, rngs)
    employees = build_employees(settings, rngs)
    assignments = build_assignments(settings, rngs, employees, master)
    performance = build_performance(settings, rngs, employees, assignments, master)
    salary = build_salary(settings, rngs, employees, assignments, performance, master)
    tenure = build_tenure(settings, employees, assignments)
    promotions = build_promotions(employees, assignments)
    return {**master, "employee": employees, "job_assignment": assignments,
            "performance_evidence": performance, "salary_record": salary,
            "tenure": tenure, "promotion": promotions}


def build_pipeline(*args, **kwargs) -> dict[str, pd.DataFrame]:
    return generate(*args, **kwargs)


def analyze(tables: dict[str, pd.DataFrame], base_currency: str = "USD") -> dict[str, pd.DataFrame]:
    """Run the Part 4 analytics stages over generated source tables."""
    salary = normalize_salary(tables["salary_record"], tables["fx_rate"], base_currency)
    metrics = calculate_metrics(salary, tables["compensation_band"])
    assignment = tables["job_assignment"][["assignment_id", "role_id", "level_id", "location_id"]]
    metrics = metrics.merge(assignment, on="assignment_id", how="left", validate="many_to_one")
    groups = build_comparable_groups(metrics, as_of_month=str(metrics["period_month"].max()))
    members = groups["comparable_group_member"]
    metrics = metrics.merge(members[["salary_record_id", "group_id"]], on="salary_record_id", how="left", validate="one_to_one")
    metrics = detect_disparities(metrics)
    return {"compensation_metrics": metrics, **groups}


def build_review_workflow(analytics: dict[str, pd.DataFrame], year: int,
                         proposed_by: str) -> dict[str, pd.DataFrame]:
    """Create Part 5 proposals from below-band and unexplained-outlier flags."""
    metrics = analytics["compensation_metrics"].copy()
    candidates = metrics[metrics["metric_flag"].eq("BELOW_BAND_MIN") |
                        metrics["disparity_flag"].eq("UNEXPLAINED_OUTLIER")].copy()
    if candidates.empty:
        return {"adjustment_proposal": pd.DataFrame(), "proposal_evidence": pd.DataFrame()}
    candidates["target_salary_fte"] = candidates.groupby("group_id")["base_salary_fte"].transform("median")
    candidates["target_salary_fte"] = candidates[["target_salary_fte", "band_min"]].max(axis=1)
    candidates["reason_code"] = candidates["metric_flag"].where(
        candidates["metric_flag"].eq("BELOW_BAND_MIN"), "UNEXPLAINED_GAP")
    evidence = candidates[["salary_record_id"]].drop_duplicates().rename(
        columns={"salary_record_id": "evidence_id"})
    evidence["salary_record_id"] = evidence["evidence_id"]
    workflow = create_proposals(candidates, year, proposed_by, evidence)
    events = pd.DataFrame(columns=["event_id", "adjustment_id", "from_status", "to_status",
                                   "actor_id", "actor_role", "event_ts", "comment"])
    for adjustment in workflow["adjustment_proposal"].itertuples(index=False):
        events = append_approval_event(events, adjustment.adjustment_id, "SUBMITTED",
                                       proposed_by, "HR_PARTNER", year)
    workflow["approval_event"] = events
    return workflow


def apply_anomalies(tables: dict[str, pd.DataFrame], seed: int,
                    rates: dict | None = None, ground_truth_dir=None):
    """Inject labelled edge cases; optionally persist labels outside inputs."""
    altered, labels = inject_anomalies(tables, seed=seed, rates=rates)
    if ground_truth_dir is not None:
        write_ground_truth(labels, ground_truth_dir)
    return altered, labels


def validate(tables: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    """Run schema and integrity checks and return grouped errors."""
    errors = validate_schema(tables)
    for table, messages in validate_tables(tables).items():
        errors.setdefault(table, []).extend(messages)
    return {table: messages for table, messages in errors.items() if messages}


def export_outputs(tables: dict[str, pd.DataFrame], directory) -> dict[str, object]:
    """Write CSV tables, a SQL seed, and a checksum manifest."""
    csv_paths = write_tables(tables, directory)
    sql_path = write_sql(tables, __import__("pathlib").Path(directory) / "seed.sql")
    manifest_path = write_manifest(directory)
    return {"csv": csv_paths, "sql": sql_path, "manifest": manifest_path}
