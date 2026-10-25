from enum import StrEnum


def default_level_names() -> dict[str, str]:
    labels = ("Нет опыта", "Начальный", "Базовый", "Уверенный", "Продвинутый", "Эксперт")
    return {str(index): label for index, label in enumerate(labels)}


def level_label(level: int, scale_type: str) -> str:
    return chr(65 + level) if scale_type == "letter" else str(level)


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
