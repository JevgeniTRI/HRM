import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

from app.config import Settings
from app.security import MAX_REQUEST_BODY_SIZE


@pytest.mark.parametrize("host", ["attacker.example", "localhost.attacker.example"])
def test_untrusted_host_cannot_access_api(client, host):
    assert client.get("/api/employees", headers={"Host": host}).status_code == 400


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://attacker.example"},
        {"Origin": "null"},
        {"Origin": "http://127.0.0.1:5173.attacker.example"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_foreign_browser_requests_do_not_change_data(client, headers):
    response = client.post("/api/departments", json={"name": "Injected"}, headers=headers)
    assert response.status_code == 403
    assert client.get("/api/departments").json() == []
    assert client.get("/api/employees", headers=headers).status_code == 403


def test_foreign_form_upload_is_blocked_before_validation(client):
    response = client.post(
        "/api/employees/1/skills/1/certificates",
        headers={"Origin": "https://attacker.example"},
        files={"file": ("cert.pdf", b"%PDF-1.4")},
    )
    assert response.status_code == 403


def test_multiple_origins_are_rejected(client):
    response = client.post(
        "/api/departments",
        json={"name": "Injected"},
        headers=[
            ("Origin", "http://127.0.0.1:5173"),
            ("Origin", "https://attacker.example"),
        ],
    )
    assert response.status_code == 403
    assert client.get("/api/departments").json() == []


def test_trusted_browser_can_read_and_write(client):
    headers = {"Origin": "http://127.0.0.1:5173"}
    response = client.post("/api/departments", json={"name": "Trusted"}, headers=headers)
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    response = client.get("/api/departments", headers=headers)
    assert response.json()[0]["name"] == "Trusted"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert (
        client.options(
            "/api/departments",
            headers={**headers, "Access-Control-Request-Method": "POST"},
        ).status_code
        == 200
    )


def test_oversized_request_is_rejected_before_business_operation(client):
    response = client.post(
        "/api/departments",
        json={"name": "Should not be created"},
        headers={"Content-Length": str(MAX_REQUEST_BODY_SIZE + 1)},
    )
    assert response.status_code == 413
    assert client.get("/api/departments").json() == []


def test_oversized_bodyless_delete_cannot_remove_data(client, department):
    response = client.delete(
        f"/api/departments/{department['id']}",
        headers={"Content-Length": str(MAX_REQUEST_BODY_SIZE + 1)},
    )
    assert response.status_code == 413
    assert client.get("/api/departments").json()[0]["id"] == department["id"]


@pytest.mark.parametrize("length", ["-1", "invalid", "1,2"])
def test_invalid_content_length_is_rejected(client, length):
    assert client.get("/api/health", headers={"Content-Length": length}).status_code == 400


def test_body_limit_counts_stream_without_content_length():
    # Use a small limit so the test checks streamed chunks without allocating MiBs.
    app = FastAPI()
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=32)

    @app.post("/")
    async def consume(request: Request):
        await request.body()
        return {"ok": True}

    def chunks():
        yield b"x" * 20
        yield b"x" * 20

    with TestClient(app) as client:
        assert client.post("/", content=chunks()).status_code == 413
        assert client.post("/", content=b"x" * 32).status_code == 200


def test_wildcard_browser_origins_are_rejected():
    with pytest.raises(ValueError, match="точные HTTP/HTTPS Origin"):
        Settings(cors_origins=["*"])
