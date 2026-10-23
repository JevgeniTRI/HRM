"""Optional examples for a demo workspace. Existing tasks are never replaced."""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Department
from app.services.common import record_activity
from app.services.tasks import task_values
from app.tasks.models import Task
from app.tasks.schemas import TaskWrite


def seed_tasks() -> None:
    with SessionLocal() as session:
        if session.scalar(select(func.count(Task.id))):
            print("Task board already contains records. Demo tasks were not added.")
            return
        departments = {dept.name: dept for dept in session.scalars(select(Department)).all()}
        today = date.today()
        examples = [
            (
                {
                    "title": "Практикум по Python",
                    "description": (
                        "Разобрать типизацию, тестирование и подходы к поддержке сервисов."
                    ),
                    "status": "todo",
                    "learning_source": "internal",
                    "learning_format": "group",
                    "participant_count": 6,
                    "duration_hours": "2",
                    "cost": "0",
                    "currency": "EUR",
                    "due_on": today + timedelta(days=7),
                },
                ["Разработка"],
            ),
            (
                {
                    "title": "Составить планы развития",
                    "description": (
                        "Согласовать цели сотрудников и приоритеты обучения на следующий месяц."
                    ),
                    "status": "todo",
                    "due_on": today + timedelta(days=5),
                },
                ["HR и администрация", "Разработка"],
            ),
            (
                {
                    "title": "Продвинутый React",
                    "description": (
                        "Внешний курс по архитектуре компонентов и производительности интерфейсов."
                    ),
                    "status": "in_progress",
                    "learning_source": "external",
                    "learning_format": "individual",
                    "participant_count": 1,
                    "duration_hours": "4",
                    "cost": "120",
                    "currency": "EUR",
                    "due_on": today + timedelta(days=10),
                },
                ["Разработка"],
            ),
            (
                {
                    "title": "Безопасная работа с данными",
                    "description": (
                        "Групповой тренинг по работе с персональными данными и доступами."
                    ),
                    "status": "in_progress",
                    "learning_source": "external",
                    "learning_format": "group",
                    "participant_count": 5,
                    "duration_hours": "3",
                    "cost": "5000",
                    "currency": "UAH",
                    "due_on": today + timedelta(days=3),
                },
                ["HR и администрация", "Маркетинг"],
            ),
            (
                {
                    "title": "Командная коммуникация",
                    "description": (
                        "Практика обратной связи: 1,5 часа, 10 участников — 15 человекочасов."
                    ),
                    "status": "done",
                    "learning_source": "internal",
                    "learning_format": "group",
                    "participant_count": 10,
                    "duration_hours": "1.5",
                    "cost": "0",
                    "currency": "EUR",
                    "due_on": today - timedelta(days=2),
                },
                ["Разработка", "Дизайн", "Маркетинг"],
            ),
            (
                {
                    "title": "Дизайн-система в Figma",
                    "description": (
                        "Воркшоп по компонентам, вариантам и передаче макетов в разработку."
                    ),
                    "status": "done",
                    "learning_source": "external",
                    "learning_format": "group",
                    "participant_count": 4,
                    "duration_hours": "2",
                    "cost": "180",
                    "currency": "EUR",
                    "due_on": today - timedelta(days=4),
                },
                ["Дизайн"],
            ),
        ]
        for values, names in examples:
            selected = [departments[name] for name in names if name in departments]
            data = TaskWrite(**values, department_ids=[department.id for department in selected])
            session.add(Task(**task_values(data), departments=selected))
        record_activity(
            session, "task", "Добавлены примеры задач", "Демонстрационная Kanban-доска: 6 карточек"
        )
        session.commit()
        print("Added 6 demo tasks to the Kanban board.")


if __name__ == "__main__":
    seed_tasks()
