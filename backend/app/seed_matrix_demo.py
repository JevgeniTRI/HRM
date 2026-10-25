"""Add fifty demo employees, seven departments and fourteen competencies.

Run explicitly with ``python -m app.seed_matrix_demo``. The operation is
additive and idempotent: existing profiles and non-empty assessments are kept.
"""

import json
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Department, Employee, EmployeeSkill, Skill, utc_now
from app.schemas import EmployeeWrite
from app.services.common import record_activity
from app.services.personnel import employee_values

DEPARTMENTS = (
    ("Продажи", "Продажи, развитие клиентов и сопровождение ключевых партнёров."),
    ("Финансы", "Бюджетирование, отчётность и финансовое планирование."),
    ("Клиентская поддержка", "Обработка обращений и развитие клиентского сервиса."),
    ("Операции", "Координация внутренних процессов и операционных проектов."),
    ("Закупки и логистика", "Закупки, складские процессы и управление поставками."),
    ("Контроль качества", "Контроль процессов, тестирование и управление качеством."),
    ("Исследования и развитие", "Исследования, прототипирование и развитие продуктов."),
)

SOFT_SKILLS = (
    "Командная работа",
    "Критическое мышление",
    "Решение проблем",
    "Адаптивность",
    "Управление временем",
    "Эмоциональный интеллект",
    "Проведение презентаций",
)

HARD_SKILLS = (
    "Excel и финансовое моделирование",
    "Power BI",
    "REST API",
    "Автоматизация тестирования",
    "Управление базами данных",
    "Информационная безопасность",
    "Бизнес-анализ",
)

FIRST_NAMES = (
    "Алексей",
    "Марина",
    "Игорь",
    "Елена",
    "Павел",
    "Наталья",
    "Виктор",
    "Ольга",
    "Сергей",
    "Ирина",
    "Андрей",
    "Ксения",
    "Максим",
    "Валерия",
    "Денис",
    "Алина",
    "Кирилл",
    "Татьяна",
    "Роман",
    "Дарья",
    "Егор",
    "Полина",
    "Антон",
    "Виктория",
    "Николай",
)

LAST_NAMES = (
    "Крылов",
    "Романова",
    "Зайцев",
    "Фомина",
    "Гаврилов",
    "Семёнова",
    "Ковалёв",
    "Данилова",
    "Комаров",
    "Миронова",
    "Андреев",
    "Крылова",
    "Павлов",
    "Сергеева",
    "Макаров",
    "Кудрявцева",
    "Титов",
    "Алексеева",
    "Ефимов",
    "Фролова",
    "Дорофеев",
    "Жукова",
    "Богданов",
    "Гусева",
    "Беляев",
    "Ильин",
    "Киселёва",
    "Осипов",
    "Васильева",
    "Николаев",
    "Медведева",
    "Савельев",
    "Баранова",
    "Григорьев",
    "Ершова",
    "Захаров",
    "Назарова",
    "Куликов",
    "Сорокина",
    "Степанов",
    "Бурова",
    "Карпов",
    "Быкова",
    "Афанасьев",
    "Тарасова",
    "Абрамов",
    "Борисова",
    "Прохоров",
    "Суслова",
    "Фёдоров",
)

POSITIONS = (
    ("Руководитель отдела продаж", "Менеджер по продажам", "Менеджер по работе с клиентами"),
    ("Финансовый директор", "Финансовый аналитик", "Экономист"),
    ("Руководитель поддержки", "Специалист поддержки", "Менеджер клиентского сервиса"),
    ("Операционный директор", "Операционный менеджер", "Координатор процессов"),
    ("Руководитель логистики", "Специалист по закупкам", "Координатор логистики"),
    ("Руководитель качества", "Инженер по качеству", "QA-специалист"),
    ("Руководитель R&D", "Исследователь", "Продуктовый аналитик"),
)


def populate_matrix_demo(session: Session, *, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    created = {"departments": 0, "employees": 0, "soft_skills": 0, "hard_skills": 0}
    departments = []
    for name, description in DEPARTMENTS:
        department = session.scalar(
            select(Department).where(Department.name_key == name.casefold())
        )
        if department is None:
            department = Department(name=name, name_key=name.casefold(), description=description)
            session.add(department)
            session.flush()
            created["departments"] += 1
            record_activity(session, "department", "Добавлено подразделение", name)
        departments.append(department)

    for category, names, counter in (
        ("Гибкие навыки", SOFT_SKILLS, "soft_skills"),
        ("Технические", HARD_SKILLS, "hard_skills"),
    ):
        for name in names:
            if session.scalar(select(Skill).where(Skill.name_key == name.casefold())) is None:
                session.add(
                    Skill(
                        name=name,
                        name_key=name.casefold(),
                        category=category,
                        description=f"Демонстрационная компетенция: {name.lower()}.",
                    )
                )
                created[counter] += 1
                record_activity(session, "skill", "Добавлена компетенция", name)
    session.flush()

    new_people = []
    managers: dict[int, int] = {}
    for index in range(50):
        email = f"matrix.demo.{index + 1:02d}@example.com"
        employee = session.scalar(select(Employee).where(Employee.email == email))
        department_index = index % len(departments)
        department = departments[department_index]
        group_index = index // len(departments)
        is_manager = group_index == 0
        if employee is None:
            first = FIRST_NAMES[index % len(FIRST_NAMES)]
            last = LAST_NAMES[index]
            titles = POSITIONS[department_index]
            position = titles[0] if is_manager else titles[1 + index % (len(titles) - 1)]
            employee = Employee(
                is_manager=is_manager,
                manager_id=None if is_manager else managers[department.id],
                **employee_values(
                    EmployeeWrite(
                        first_name=first,
                        last_name=last,
                        email=email,
                        position=position,
                        department_id=department.id,
                        hired_at=today - timedelta(days=45 + index * 17),
                        about="Развиваю профессиональные и командные компетенции.",
                        experience=f"Опыт работы по направлению «{department.name}».",
                        education="Высшее образование и профильное дополнительное обучение.",
                    )
                ),
            )
            session.add(employee)
            session.flush()
            created["employees"] += 1
            record_activity(
                session,
                "employee",
                "Добавлен сотрудник",
                f"{first} {last} · {position}",
                employee.id,
            )
        if is_manager:
            managers[department.id] = employee.id
        new_people.append(employee)

    skills = session.scalars(select(Skill).order_by(Skill.id)).all()
    employees = session.scalars(select(Employee).order_by(Employee.id)).all()
    assessments = {
        (item.employee_id, item.skill_id): item
        for item in session.scalars(select(EmployeeSkill)).all()
    }
    rng = random.Random(20261025)
    created_assessments = 0
    normalized_assessments = 0
    now = utc_now()
    for employee in employees:
        for skill in skills:
            key = (employee.id, skill.id)
            assessment = assessments.get(key)
            if assessment is None:
                current = rng.randint(0, 5)
                session.add(
                    EmployeeSkill(
                        employee_id=employee.id,
                        skill_id=skill.id,
                        current_level=current,
                        target_level=rng.randint(current, 5),
                        updated_at=now,
                    )
                )
                created_assessments += 1
                continue
            changed = False
            if assessment.current_level is None:
                assessment.current_level = rng.randint(0, 5)
                changed = True
            if assessment.target_level < assessment.current_level:
                assessment.target_level = assessment.current_level
                changed = True
            if changed:
                assessment.updated_at = now
                normalized_assessments += 1

    return {
        **created,
        "assessments": created_assessments,
        "normalized_assessments": normalized_assessments,
        "total_employees": len(employees),
        "total_skills": len(skills),
    }


def main() -> None:
    with SessionLocal.begin() as session:
        result = populate_matrix_demo(session)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
