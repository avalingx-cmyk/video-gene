import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CostAlertLevel(Enum):
    OK = "ok"
    WARNING = "warning"
    HARD_STOP = "hard_stop"


@dataclass
class CostAlert:
    level: CostAlertLevel
    message: str
    user_cost: float
    project_cost: float
    user_cap: Optional[float]
    project_cap: Optional[float]
    user_percent: float
    project_percent: float
    can_override: bool = False


def check_cost_alert(
    user_cost: float,
    project_cost: float,
    user_cap: Optional[float],
    project_cap: Optional[float],
    alert_threshold: float = 0.8,
    hard_stop_threshold: float = 1.0,
) -> CostAlert:
    user_percent = (user_cost / user_cap) if user_cap and user_cap > 0 else 0.0
    project_percent = (project_cost / project_cap) if project_cap and project_cap > 0 else 0.0

    max_percent = max(user_percent, project_percent)

    if max_percent >= hard_stop_threshold:
        return CostAlert(
            level=CostAlertLevel.HARD_STOP,
            message=f"Cost limit reached ({max_percent*100:.0f}%). Hard stop triggered.",
            user_cost=user_cost,
            project_cost=project_cost,
            user_cap=user_cap,
            project_cap=project_cap,
            user_percent=user_percent,
            project_percent=project_percent,
            can_override=True,
        )

    if max_percent >= alert_threshold:
        return CostAlert(
            level=CostAlertLevel.WARNING,
            message=f"Cost alert: {max_percent*100:.0f}% of cap reached",
            user_cost=user_cost,
            project_cost=project_cost,
            user_cap=user_cap,
            project_cap=project_cap,
            user_percent=user_percent,
            project_percent=project_percent,
            can_override=True,
        )

    return CostAlert(
        level=CostAlertLevel.OK,
        message=f"Cost OK: {max_percent*100:.0f}% of cap",
        user_cost=user_cost,
        project_cost=project_cost,
        user_cap=user_cap,
        project_cap=project_cap,
        user_percent=user_percent,
        project_percent=project_percent,
        can_override=False,
    )


def should_stop_for_cost(
    user_cost: float,
    project_cost: float,
    user_cap: Optional[float],
    project_cap: Optional[float],
    override: bool = False,
    alert_threshold: float = 0.8,
    hard_stop_threshold: float = 1.0,
) -> tuple[bool, Optional[CostAlert]]:
    alert = check_cost_alert(user_cost, project_cost, user_cap, project_cap, alert_threshold, hard_stop_threshold)

    if alert.level == CostAlertLevel.HARD_STOP and not override:
        return True, alert

    return False, alert
