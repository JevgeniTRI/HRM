from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import (
    certificates,
    dashboard,
    departments,
    employees,
    imports,
    integrations,
    skills,
    teams,
)
from app.auth import LoginLimiter, accounts_router, authorize
from app.auth import router as auth_router
from app.config import get_settings
from app.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PayloadTooLargeError,
    ValidationError,
)
from app.security import MAX_REQUEST_BODY_SIZE, BrowserRequestMiddleware
from app.services.data_import import ImportRejected
from app.tasks.router import router as tasks_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HRM · People & Skills",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.login_limiter = LoginLimiter()
    app.include_router(auth_router, prefix="/api")
    app.include_router(accounts_router, prefix="/api")
    app.include_router(integrations.router, prefix="/api")

    @app.exception_handler(ImportRejected)
    async def import_rejected(_, error: ImportRejected):
        return JSONResponse(status_code=422, content={"detail": str(error), "errors": error.errors})

    @app.exception_handler(NotFoundError)
    async def not_found(_, error: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ConflictError)
    async def conflict(_, error: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(ValidationError)
    async def invalid_input(_, error: ValidationError):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(PayloadTooLargeError)
    async def payload_too_large(_, error: PayloadTooLargeError):
        return JSONResponse(status_code=413, content={"detail": str(error)})

    @app.exception_handler(ForbiddenError)
    async def forbidden(_, error: ForbiddenError):
        return JSONResponse(status_code=403, content={"detail": str(error)})

    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_REQUEST_BODY_SIZE)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-HRM-Request", "Authorization"],
    )
    app.add_middleware(BrowserRequestMiddleware, allowed_origins=settings.cors_origins)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts, www_redirect=False
    )
    for router in (
        employees.router,
        departments.router,
        skills.router,
        certificates.router,
        dashboard.router,
        tasks_router,
        teams.router,
        imports.router,
    ):
        app.include_router(router, prefix="/api", dependencies=[Depends(authorize)])

    @app.get("/api/health", tags=["Система"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
