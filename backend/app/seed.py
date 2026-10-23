"""Explicit, atomic demo data initialization. Never runs at application startup."""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Activity, Department, Employee, EmployeeSkill, Skill, utc_now
from app.schemas import EmployeeWrite
from app.services.personnel import employee_values


def seed() -> None:
    with SessionLocal() as session:
        if (
            session.scalar(select(func.count(Employee.id)))
            or session.scalar(select(func.count(Department.id)))
            or session.scalar(select(func.count(Skill.id)))
        ):
            print("База уже содержит данные. Демонстрационные записи не добавлены.")
            return
        department_data = [
            ("Разработка", "Продуктовая разработка, архитектура и качество кода"),
            ("Дизайн", "Продуктовый дизайн, исследования и визуальные коммуникации"),
            ("Маркетинг", "Развитие бренда, контент и привлечение клиентов"),
            ("HR и администрация", "Подбор, развитие команды и операционные процессы"),
        ]
        departments = [
            Department(name=name, name_key=name.casefold(), description=description)
            for name, description in department_data
        ]
        session.add_all(departments)
        skill_data = [
            ("Python", "Технические", "Разработка сервисов, работа с типами и тестирование."),
            ("React", "Технические", "Компоненты, состояние приложения и доступные интерфейсы."),
            ("SQL", "Технические", "Моделирование данных, запросы и оптимизация."),
            ("Figma", "Дизайн", "Макеты, прототипы и дизайн-системы."),
            (
                "Коммуникация",
                "Гибкие навыки",
                "Ясное общение, обратная связь и взаимодействие в команде.",
            ),
            ("Управление проектами", "Управление", "Планирование, координация и работа с рисками."),
            ("Аналитика", "Технические", "Работа с данными и проверка гипотез."),
            ("Английский язык", "Языки", "Общение и работа с профессиональными материалами."),
        ]
        skills = [
            Skill(name=name, name_key=name.casefold(), category=category, description=description)
            for name, category, description in skill_data
        ]
        session.add_all(skills)
        session.flush()
        people = [
            (
                "Анна",
                "Морозова",
                "anna.morozova",
                "Frontend-разработчик",
                0,
                "active",
                [1, 4, 7],
                [4, 4, 3],
            ),
            (
                "Дмитрий",
                "Волков",
                "dmitry.volkov",
                "Backend-разработчик",
                0,
                "active",
                [0, 2, 4, 7],
                [4, 3, 4, 4],
            ),
            (
                "Екатерина",
                "Лебедева",
                "ekaterina.lebedeva",
                "Product designer",
                1,
                "active",
                [3, 4, 6],
                [5, 4, 3],
            ),
            (
                "Александр",
                "Соколов",
                "alexander.sokolov",
                "Team Lead",
                0,
                "active",
                [0, 2, 4, 5],
                [5, 4, 4, 5],
            ),
            ("Мария", "Козлова", "maria.kozlova", "HR-менеджер", 3, "active", [4, 5, 7], [5, 4, 3]),
            ("Иван", "Попов", "ivan.popov", "Маркетолог", 2, "leave", [4, 6, 7], [4, 4, 4]),
            (
                "Ольга",
                "Новикова",
                "olga.novikova",
                "UX-исследователь",
                1,
                "active",
                [3, 4, 6],
                [4, 5, 4],
            ),
            ("Михаил", "Орлов", "mikhail.orlov", "QA-инженер", 0, "active", [0, 2, 4], [3, 4, 4]),
            (
                "Анастасия",
                "Белова",
                "anastasia.belova",
                "Контент-менеджер",
                2,
                "active",
                [4, 6, 7],
                [4, 3, 4],
            ),
            (
                "Артём",
                "Кузнецов",
                "artem.kuznetsov",
                "Python-разработчик",
                0,
                "probation",
                [0, 2, 4, 7],
                [2, 3, None, 3],
            ),
            (
                "София",
                "Петрова",
                "sofia.petrova",
                "UI-дизайнер",
                1,
                "probation",
                [3, 4, 7],
                [3, None, 3],
            ),
            (
                "Никита",
                "Смирнов",
                "nikita.smirnov",
                "Аналитик данных",
                2,
                "active",
                [0, 2, 6, 4],
                [3, 4, 4, 4],
            ),
        ]
        today = date.today()
        now = utc_now()
        for index, (first, last, email, position, dept, status, skill_ids, levels) in enumerate(
            people
        ):
            employee = Employee(
                **employee_values(
                    EmployeeWrite(
                        first_name=first,
                        last_name=last,
                        email=f"{email}@example.com",
                        position=position,
                        department_id=departments[dept].id,
                        status=status,
                        hired_at=today - timedelta(days=(len(people) - index) * 25),
                    )
                )
            )
            session.add(employee)
            session.flush()
            for skill_index, level in zip(skill_ids, levels, strict=True):
                session.add(
                    EmployeeSkill(
                        employee_id=employee.id,
                        skill_id=skills[skill_index].id,
                        current_level=level,
                        target_level=4,
                        updated_at=now - timedelta(hours=len(people) - index),
                    )
                )
            if index > 5:
                session.add(
                    Activity(
                        kind="employee",
                        title="Добавлен сотрудник",
                        detail=f"{first} {last} · {position}",
                        employee_id=employee.id,
                        created_at=now - timedelta(hours=(len(people) - index) * 2),
                    )
                )
        session.add(
            Activity(
                kind="assessment",
                title="Обновлена оценка навыка",
                detail="Анна Морозова · React: 4, цель 4",
                employee_id=1,
                created_at=now - timedelta(minutes=35),
            )
        )
        session.commit()
        print("Добавлено 12 демонстрационных сотрудников, 4 подразделения и 8 навыков.")


if __name__ == "__main__":
    seed()
    from app.tasks.seed import seed_tasks

    seed_tasks()
