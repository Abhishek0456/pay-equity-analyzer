"""Part 5 approval state machine."""
from datetime import datetime, timezone
import pandas as pd
from payequity.ids import approval_event_id

TRANSITIONS = {None: {"SUBMITTED"}, "DRAFT": {"SUBMITTED", "WITHDRAWN"}, "SUBMITTED": {"MANAGER_APPROVED", "REJECTED", "WITHDRAWN"}, "MANAGER_APPROVED": {"HR_APPROVED", "REJECTED"}, "HR_APPROVED": {"APPLIED", "REJECTED"}}

def append_approval_event(events, adjustment_id, to_status, actor_id, actor_role, year, comment=None):
    prior = events[events["adjustment_id"].eq(adjustment_id)] if not events.empty else events
    current = prior.iloc[-1]["to_status"] if not prior.empty else None
    if to_status not in TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid transition {current!r} -> {to_status!r}")
    if actor_role not in {"MANAGER", "HR_PARTNER", "SYS_ADMIN"}:
        raise ValueError("invalid actor_role")
    row = {"event_id": approval_event_id(year, len(events) + 1), "adjustment_id": adjustment_id, "from_status": current, "to_status": to_status, "actor_id": actor_id, "actor_role": actor_role, "event_ts": datetime.now(timezone.utc).isoformat(), "comment": comment}
    return pd.concat([events, pd.DataFrame([row])], ignore_index=True)

def add_event(*args, **kwargs):
    return append_approval_event(*args, **kwargs)
