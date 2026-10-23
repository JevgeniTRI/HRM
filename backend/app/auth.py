"""Cookie sessions, account administration and server-side authorization."""

import hashlib
import hmac
import re
import secrets
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.dependencies import DB
from app.models import Account, AuthSession, Employee
from app.permissions import Principal, employee_scope, task_scope
from app.services.common import record_activity
from app.tasks.models import Task

COOKIE = "hrm_session"
Role = Literal["admin", "power_user", "manager", "employee"]
Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.@+\-]+$"
    ),
]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
router = APIRouter(prefix="/auth", tags=["Авторизация"])
accounts_router = APIRouter(prefix="/accounts", tags=["Аккаунты"])


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=5, maxmem=64 * 1024 * 1024
    ).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, _ = encoded.split("$")
        return algorithm == "scrypt" and hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False


DUMMY_HASH = password_hash(secrets.token_urlsafe(24))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_guard(request: Request):
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and request.headers.get("x-hrm-request") != "1"
    ):
        raise HTTPException(403, "Отсутствует защита запроса. Обновите страницу")


def current_account(request: Request, session: DB) -> Account:
    csrf_guard(request)
    token = request.cookies.get(COOKIE, "")
    account = (
        session.scalar(
            select(Account)
            .join(AuthSession, AuthSession.account_id == Account.id)
            .where(
                AuthSession.token_hash == token_hash(token),
                AuthSession.expires_at > datetime.now(UTC),
                Account.is_active.is_(True),
            )
        )
        if token
        else None
    )
    if account is None:
        raise HTTPException(401, "Войдите в систему")
    employee = account.employee
    session.info["actor_username"] = account.username
    session.info["actor"] = Principal(
        account.id, account.role, account.employee_id, employee.department_id if employee else None
    )
    return account


CurrentAccount = Annotated[Account, Depends(current_account)]


def admin_account(account: CurrentAccount):
    if account.role != "admin":
        raise HTTPException(403, "Управлять аккаунтами может только администратор")
    return account


AdminAccount = Annotated[Account, Depends(admin_account)]


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: Role
    employee_id: int | None
    is_active: bool


def identity(account: Account):
    return {
        **AccountRead.model_validate(account).model_dump(),
        "department_id": account.employee.department_id if account.employee else None,
        "display_name": f"{account.employee.first_name} {account.employee.last_name}"
        if account.employee
        else account.username,
    }


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class LoginLimiter:
    def __init__(self):
        self.entries = defaultdict(deque)
        self.lock = Lock()

    def check(self, key):
        now = monotonic()
        with self.lock:
            for address in list(self.entries):
                while self.entries[address] and self.entries[address][0] < now - 900:
                    self.entries[address].popleft()
                if not self.entries[address]:
                    del self.entries[address]
            attempts = self.entries[key]
            if len(attempts) >= 30 or sum(t > now - 60 for t in attempts) >= 10:
                raise HTTPException(
                    429,
                    "Слишком много попыток входа. Попробуйте позже",
                    headers={"Retry-After": "60"},
                )
            attempts.append(now)
            return now

    def success(self, key, ticket):
        with self.lock:
            attempts = self.entries.get(key)
            if attempts and ticket in attempts:
                attempts.remove(ticket)


@router.post("/login")
def login(data: Login, request: Request, response: Response, session: DB):
    csrf_guard(request)
    address = request.client.host if request.client else "unknown"
    ticket = request.app.state.login_limiter.check(address)
    account = session.scalar(
        select(Account).where(Account.username == data.username.strip().casefold())
    )
    valid = verify_password(data.password, account.password_hash if account else DUMMY_HASH)
    if not valid or account is None or not account.is_active:
        raise HTTPException(401, "Неверный логин или пароль")
    request.app.state.login_limiter.success(address, ticket)
    old_token = request.cookies.get(COOKIE)
    if old_token:
        session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(old_token)))
    session.execute(delete(AuthSession).where(AuthSession.expires_at <= datetime.now(UTC)))
    token = secrets.token_urlsafe(32)
    seconds = get_settings().session_hours * 3600
    session.add(
        AuthSession(
            token_hash=token_hash(token),
            account_id=account.id,
            expires_at=datetime.now(UTC) + timedelta(seconds=seconds),
        )
    )
    session.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=seconds,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
        path="/",
    )
    return identity(account)


@router.get("/me")
def me(account: CurrentAccount):
    return identity(account)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, session: DB):
    csrf_guard(request)
    session.execute(
        delete(AuthSession).where(
            AuthSession.token_hash == token_hash(request.cookies.get(COOKIE, ""))
        )
    )
    session.commit()
    response.delete_cookie(
        COOKIE, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="strict"
    )


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: Password


@router.put("/password", status_code=204)
def change_password(data: PasswordChange, account: CurrentAccount, session: DB, response: Response):
    if not verify_password(data.current_password, account.password_hash):
        raise HTTPException(400, "Текущий пароль указан неверно")
    account.password_hash = password_hash(data.new_password)
    record_activity(session, "account", "Изменён пароль", account.username)
    session.execute(delete(AuthSession).where(AuthSession.account_id == account.id))
    session.commit()
    response.delete_cookie(COOKIE, path="/")


class AccountWrite(BaseModel):
    username: Username
    role: Role
    employee_id: int | None = Field(default=None, gt=0)
    is_active: bool = True


class AccountCreate(AccountWrite):
    password: Password


def validate_link(data: AccountWrite, session):
    if data.role != "admin" and data.employee_id is None:
        raise HTTPException(422, "Выберите карточку сотрудника")
    if data.employee_id is not None and session.get(Employee, data.employee_id) is None:
        raise HTTPException(422, "Сотрудник не найден")


def commit_account(session):
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Логин или сотрудник уже связан с другим аккаунтом") from exc


@accounts_router.get("", response_model=list[AccountRead])
def list_accounts(_: AdminAccount, session: DB):
    return session.scalars(select(Account).order_by(Account.username)).all()


@accounts_router.post("", response_model=AccountRead, status_code=201)
def create_account(data: AccountCreate, _: AdminAccount, session: DB):
    validate_link(data, session)
    account = Account(
        **data.model_dump(exclude={"password", "username"}),
        username=data.username.casefold(),
        password_hash=password_hash(data.password),
    )
    session.add(account)
    record_activity(session, "account", "Создан аккаунт", f"{account.username} · {account.role}")
    commit_account(session)
    return account


def require_account(session, account_id):
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(404, "Аккаунт не найден")
    return account


@accounts_router.put("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, data: AccountWrite, actor: AdminAccount, session: DB):
    account = require_account(session, account_id)
    validate_link(data, session)
    if account.id == actor.id and (data.role != "admin" or not data.is_active):
        raise HTTPException(
            409, "Нельзя отключить свой аккаунт или снять с себя роль администратора"
        )
    if (
        account.role == "admin"
        and account.is_active
        and (data.role != "admin" or not data.is_active)
    ):
        admins = session.scalar(
            select(func.count(Account.id)).where(
                Account.role == "admin", Account.is_active.is_(True)
            )
        )
        if admins <= 1:
            raise HTTPException(409, "В системе должен остаться активный администратор")
    for key, value in data.model_dump().items():
        setattr(account, key, value.casefold() if key == "username" else value)
    session.execute(delete(AuthSession).where(AuthSession.account_id == account.id))
    record_activity(session, "account", "Обновлён доступ", f"{account.username} · {account.role}")
    commit_account(session)
    return account


class PasswordReset(BaseModel):
    password: Password


@accounts_router.put("/{account_id}/password", status_code=204)
def reset_password(account_id: int, data: PasswordReset, _: AdminAccount, session: DB):
    account = require_account(session, account_id)
    account.password_hash = password_hash(data.password)
    record_activity(session, "account", "Сброшен пароль аккаунта", account.username)
    session.execute(delete(AuthSession).where(AuthSession.account_id == account.id))
    session.commit()


def authorize(request: Request, account: CurrentAccount, session: DB):
    """Deny unknown operations; collection queries additionally apply data scopes."""
    path = request.url.path.removeprefix("/api")
    method = request.method
    actor = session.info["actor"]
    if actor.global_access:
        return
    employee_match = re.fullmatch(
        r"/employees/(\d+)(?:/skills/\d+(?:/certificates(?:/\d+(?:/file)?)?)?)?", path
    )
    if employee_match:
        employee_id = int(employee_match[1])
        person = session.scalar(
            select(Employee).where(Employee.id == employee_id, employee_scope(session))
        )
        if person is None:
            raise HTTPException(404, "Сотрудник не найден")
        if method == "DELETE" and re.fullmatch(r"/employees/\d+", path):
            raise HTTPException(
                403, "Удалять сотрудников могут администратор и пользователь с повышенными правами"
            )
        return
    if path in {"/employees", "/departments", "/skills"} and method == "GET":
        return
    if (
        path in {"/matrix", "/dashboard", "/employees/export"}
        and method == "GET"
        and actor.role == "manager"
    ):
        return
    if path in {"/tasks", "/tasks/summary", "/tasks/estimate"}:
        return
    task_match = re.fullmatch(r"/tasks/(\d+)(?:/status)?", path)
    if task_match:
        task = session.scalar(
            select(Task).where(Task.id == int(task_match[1]), task_scope(session))
        )
        if task is None:
            raise HTTPException(404, "Задача не найдена")
        if actor.role == "employee" and method == "DELETE":
            raise HTTPException(403, "Удалять назначенные задачи может руководитель")
        return
    raise HTTPException(403, "Недостаточно прав")
