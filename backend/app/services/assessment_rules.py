from enum import StrEnum


class AssessmentState(StrEnum):
    UNASSESSED = "unassessed"
    MET = "met"
    GAP = "gap"


def assessment_state(current_level: int | None, target_level: int) -> AssessmentState:
    if current_level is None:
        return AssessmentState.UNASSESSED
    return AssessmentState.MET if current_level >= target_level else AssessmentState.GAP


def coverage(at_target: int, assigned: int) -> int:
    return round(at_target / assigned * 100) if assigned else 0
