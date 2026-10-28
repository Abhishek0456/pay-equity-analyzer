import pandas as pd
import pytest

from payequity.workflow.approvals import append_approval_event


def test_approval_events_are_append_only():
    events = pd.DataFrame(columns=["adjustment_id", "to_status"])
    events = append_approval_event(events, "ADJ-1", "SUBMITTED", "EMP-1", "HR_PARTNER", 2026)
    assert len(events) == 1
    assert events.loc[0, "from_status"] is None


def test_invalid_approval_transition_is_rejected():
    events = pd.DataFrame([{"adjustment_id": "ADJ-1", "to_status": "SUBMITTED"}])
    with pytest.raises(ValueError, match="invalid transition"):
        append_approval_event(events, "ADJ-1", "APPLIED", "EMP-1", "SYS_ADMIN", 2026)
