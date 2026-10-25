"""Explicit, additive demo organization: python -m app.seed_expansion.

Creates five teams with one manager and twelve employees each. Never runs on
startup, never replaces existing profiles/passwords, and commits as one unit.
The short initial password is intentional for these local demonstration users.
"""

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import password_hash
from app.database import SessionLocal
from app.models import Account, Department, Employee
from app.schemas import EmployeeWrite
from app.services.common import record_activity
from app.services.organization import reconcile_managers
from app.services.personnel import employee_values

Person = tuple[str, str, str]


@dataclass(frozen=True)
class Team:
    name: str
    description: str
    manager_title: str
    manager: Person
    members: tuple[Person, ...]
    positions: tuple[str, ...]
    focus: str
    education: str


TEAMS = (
    Team(
        "Продажи",
        "Развитие продаж, сопровождение клиентов и работа с ключевыми партнёрами.",
        "Руководитель отдела продаж",
        ("Сергей", "Крылов", "sergey.krylov"),
        (
            ("Андрей", "Мельников", "andrey.melnikov"),
            ("Ксения", "Романова", "kseniya.romanova"),
            ("Максим", "Зайцев", "maksim.zaytsev"),
            ("Валерия", "Фомина", "valeriya.fomina"),
            ("Олег", "Гаврилов", "oleg.gavrilov"),
            ("Юлия", "Семёнова", "yuliya.semenova"),
            ("Егор", "Ковалёв", "egor.kovalev"),
            ("Полина", "Данилова", "polina.danilova"),
            ("Вадим", "Комаров", "vadim.komarov"),
            ("Вероника", "Миронова", "veronika.mironova"),
            ("Тимур", "Андреев", "timur.andreev"),
            ("Елизавета", "Крылова", "elizaveta.krylova"),
        ),
        (
            "Менеджер по продажам B2B",
            "Менеджер по работе с ключевыми клиентами",
            "Региональный менеджер по продажам",
            "Специалист по развитию продаж",
        ),
        "переговоры, развитие клиентской базы и долгосрочные партнёрства",
        "Высшее образование: коммерция и управление продажами",
    ),
    Team(
        "Финансы",
        "Бюджетирование, управленческий учёт, финансовое планирование и контроль расходов.",
        "Руководитель финансового отдела",
        ("Елена", "Виноградова", "elena.vinogradova"),
        (
            ("Виктор", "Павлов", "viktor.pavlov"),
            ("Наталья", "Сергеева", "natalya.sergeeva"),
            ("Игорь", "Макаров", "igor.makarov"),
            ("Татьяна", "Кудрявцева", "tatyana.kudryavtseva"),
            ("Алексей", "Титов", "aleksey.titov"),
            ("Светлана", "Алексеева", "svetlana.alekseeva"),
            ("Борис", "Ефимов", "boris.efimov"),
            ("Людмила", "Фролова", "lyudmila.frolova"),
            ("Виталий", "Дорофеев", "vitaliy.dorofeev"),
            ("Галина", "Жукова", "galina.zhukova"),
            ("Глеб", "Богданов", "gleb.bogdanov"),
            ("Дарья", "Гусева", "darya.guseva"),
        ),
        ("Финансовый аналитик", "Бухгалтер", "Экономист", "Специалист по бюджетированию"),
        "финансовая отчётность, планирование бюджета и контроль затрат",
        "Высшее образование: экономика, финансы и кредит",
    ),
    Team(
        "Поддержка клиентов",
        "Обработка обращений, техническая поддержка и развитие клиентского сервиса.",
        "Руководитель отдела поддержки клиентов",
        ("Павел", "Беляев", "pavel.belyaev"),
        (
            ("Денис", "Ильин", "denis.ilin"),
            ("Марина", "Киселёва", "marina.kiseleva"),
            ("Кирилл", "Осипов", "kirill.osipov"),
            ("Алина", "Васильева", "alina.vasileva"),
            ("Антон", "Николаев", "anton.nikolaev"),
            ("Виктория", "Медведева", "viktoriya.medvedeva"),
            ("Станислав", "Савельев", "stanislav.savelev"),
            ("Надежда", "Баранова", "nadezhda.baranova"),
            ("Ярослав", "Григорьев", "yaroslav.grigorev"),
            ("Кристина", "Ершова", "kristina.ershova"),
            ("Марк", "Захаров", "mark.zakharov"),
            ("Диана", "Назарова", "diana.nazarova"),
        ),
        (
            "Специалист клиентской поддержки",
            "Инженер технической поддержки",
            "Специалист по качеству сервиса",
            "Менеджер по сопровождению клиентов",
        ),
        "решение обращений, база знаний и качество клиентского сервиса",
        "Высшее образование: информационные системы и сервис",
    ),
    Team(
        "Операционная деятельность",
        "Координация внутренних процессов, закупок, логистики и операционных проектов.",
        "Руководитель операционного отдела",
        ("Ирина", "Тихонова", "irina.tikhonova"),
        (
            ("Арсений", "Куликов", "arseniy.kulikov"),
            ("Евгения", "Сорокина", "evgeniya.sorokina"),
            ("Руслан", "Степанов", "ruslan.stepanov"),
            ("Алла", "Бурова", "alla.burova"),
            ("Семён", "Карпов", "semen.karpov"),
            ("Ульяна", "Быкова", "ulyana.bykova"),
            ("Леонид", "Афанасьев", "leonid.afanasev"),
            ("Яна", "Тарасова", "yana.tarasova"),
            ("Филипп", "Абрамов", "filipp.abramov"),
            ("Оксана", "Борисова", "oksana.borisova"),
            ("Матвей", "Прохоров", "matvey.prokhorov"),
            ("Лилия", "Суслова", "liliya.suslova"),
        ),
        (
            "Операционный менеджер",
            "Специалист по закупкам",
            "Координатор логистики",
            "Специалист по бизнес-процессам",
        ),
        "согласование процессов, закупки, логистика и повышение эффективности",
        "Высшее образование: менеджмент и управление бизнес-процессами",
    ),
    Team(
        "Аналитика",
        "Исследование данных, продуктовая аналитика, BI-отчётность и проверка гипотез.",
        "Руководитель отдела аналитики",
        ("Роман", "Фёдоров", "roman.fedorov"),
        (
            ("Вячеслав", "Суханов", "vyacheslav.sukhanov"),
            ("Арина", "Нестерова", "arina.nesterova"),
            ("Владислав", "Логинов", "vladislav.loginov"),
            ("Снежана", "Воронцова", "snezhana.vorontsova"),
            ("Георгий", "Мартынов", "georgiy.martynov"),
            ("Милана", "Пахомова", "milana.pakhomova"),
            ("Даниил", "Белов", "daniil.belov"),
            ("Элина", "Трофимова", "elina.trofimova"),
            ("Николай", "Рябов", "nikolay.ryabov"),
            ("Василиса", "Горбачёва", "vasilisa.gorbacheva"),
            ("Пётр", "Филатов", "petr.filatov"),
            ("Агата", "Чернова", "agata.chernova"),
        ),
        ("Продуктовый аналитик", "BI-аналитик", "Бизнес-аналитик", "Аналитик данных"),
        "анализ данных, визуализация показателей и проверка продуктовых гипотез",
        "Высшее образование: прикладная математика и анализ данных",
    ),
)


def populate_organization(session: Session, *, today: date | None = None) -> dict:
    """Stage additions in the caller's transaction, preserving existing data."""
    today = today or date.today()
    created = {"departments": 0, "employees": 0, "accounts": 0}
    users = []
    for team_index, team in enumerate(TEAMS):
        department = session.scalar(
            select(Department).where(Department.name_key == team.name.casefold())
        )
        if department is None:
            department = Department(
                name=team.name, name_key=team.name.casefold(), description=team.description
            )
            session.add(department)
            session.flush()
            created["departments"] += 1
            record_activity(session, "department", "Добавлено подразделение", team.name)

        manager_id = None
        for person_index, (first, last, username) in enumerate((team.manager, *team.members)):
            role = "manager" if person_index == 0 else "employee"
            position = (
                team.manager_title
                if role == "manager"
                else team.positions[(person_index - 1) % len(team.positions)]
            )
            email = f"{username}@example.com"
            employee = session.scalar(select(Employee).where(Employee.email == email))
            if employee is None:
                hired_days_ago = (
                    1250 + team_index * 73
                    if role == "manager"
                    else 30 + (12 - person_index) * 43 + team_index * 19
                )
                employee = Employee(
                    is_manager=role == "manager",
                    manager_id=manager_id,
                    **employee_values(
                        EmployeeWrite(
                            first_name=first,
                            last_name=last,
                            email=email,
                            position=position,
                            department_id=department.id,
                            hired_at=today - timedelta(days=hired_days_ago),
                            about=(
                                f"Профессиональные интересы: {team.focus}. "
                                "Ценю ясную коммуникацию и ответственность за результат."
                            ),
                            experience=(
                                f"Опыт работы — {8 if role == 'manager' else 3 + person_index % 6} "
                                f"лет. Текущая должность: {position}.\n"
                                + (
                                    "Руковожу командой из 12 сотрудников, планирую работу, "
                                    "развиваю компетенции и контролирую качество результата."
                                    if role == "manager"
                                    else f"Основные направления работы: {team.focus}. "
                                    "Участвую в командных проектах и улучшении рабочих процессов."
                                )
                            ),
                            education=(
                                f"{team.education}.\nДополнительная подготовка: "
                                + (
                                    "управление командой, наставничество и планирование."
                                    if role == "manager"
                                    else "профессиональные инструменты и деловая коммуникация."
                                )
                            ),
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
            elif employee.department_id != department.id:
                raise ValueError(f"Email {email} уже принадлежит сотруднику другого отдела")

            if role == "manager":
                manager_id = employee.id

            account = session.scalar(select(Account).where(Account.username == username))
            if account is None:
                if session.scalar(select(Account.id).where(Account.employee_id == employee.id)):
                    raise ValueError(f"У сотрудника {email} уже есть другой аккаунт")
                account = Account(
                    username=username,
                    password_hash=password_hash("123"),
                    role=role,
                    employee_id=employee.id,
                    is_active=True,
                )
                session.add(account)
                session.flush()
                created["accounts"] += 1
            elif account.employee_id != employee.id or account.role not in {"employee", "manager"}:
                raise ValueError(f"Аккаунт {username} уже занят или имеет другую роль")
            users.append(
                {
                    "department": department.name,
                    "full_name": f"{employee.first_name} {employee.last_name}",
                    "position": employee.position,
                    "role": account.role,
                    "username": account.username,
                    "employee_id": employee.id,
                    "department_id": department.id,
                }
            )
    reconcile_managers(session, [user["employee_id"] for user in users])
    for user in users:
        user["role"] = (
            "manager" if session.get(Employee, user["employee_id"]).is_manager else "employee"
        )
    return {"created": created, "users": users}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="Сохранить список аккаунтов в CSV")
    args = parser.parse_args()
    with SessionLocal.begin() as session:
        result = populate_organization(session)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=list(result["users"][0]), delimiter=";")
            writer.writeheader()
            writer.writerows(result["users"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
