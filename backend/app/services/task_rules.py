from decimal import Decimal
from enum import StrEnum

from app.errors import ValidationError


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class LearningSource(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class LearningFormat(StrEnum):
    INDIVIDUAL = "individual"
    GROUP = "group"


class Currency(StrEnum):
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


def validate_task(
    *,
    learning_source: LearningSource | None,
    learning_format: LearningFormat | None,
    participant_count: int | None,
    duration_hours: Decimal | None,
    cost: Decimal | None,
    currency: Currency | None,
    department_ids: list[int],
) -> None:
    if len(department_ids) != len(set(department_ids)):
        raise ValidationError("Подразделения не должны повторяться")
    if learning_source is None:
        if any(value is not None for value in (learning_format, participant_count, duration_hours)):
            raise ValidationError("Для обычной задачи параметры обучения должны быть пустыми")
    else:
        if learning_format is None or participant_count is None:
            raise ValidationError("Для обучения укажите формат и число участников")
        if learning_format == LearningFormat.INDIVIDUAL and participant_count != 1:
            raise ValidationError("Индивидуальное обучение рассчитано на одного участника")
        if learning_format == LearningFormat.GROUP and participant_count < 2:
            raise ValidationError("Для группового обучения нужно минимум два участника")
    if (cost is None) != (currency is None):
        raise ValidationError("Стоимость и валюта должны быть указаны вместе")


def to_hundredths(value: Decimal | None) -> int | None:
    return int(value * 100) if value is not None else None


def from_hundredths(value: int | None) -> Decimal | None:
    return Decimal(value) / 100 if value is not None else None


def person_hours(duration_hundredths: int | None, participants: int | None) -> Decimal | None:
    """Compute total attendance effort; unknown duration stays unknown, not zero."""
    if duration_hundredths is None or participants is None:
        return None
    return from_hundredths(duration_hundredths * participants)
