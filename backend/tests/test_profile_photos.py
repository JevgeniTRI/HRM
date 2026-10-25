from pathlib import Path

import pytest

from app.auth import password_hash
from app.config import get_settings
from app.database import get_session
from app.errors import NotFoundError
from app.models import Account, Employee
from app.storage import profile_photo_path

PNG = b"\x89PNG\r\n\x1a\nprofile-photo"
JPEG = b"\xff\xd8\xffprofile-photo"


def stored_photos():
    return list((get_settings().media_root / "profile-photos").glob("*"))


def test_upload_replace_read_and_delete_profile_photo(client, employee):
    url = f"/api/employees/{employee['id']}/photo"
    assert employee["has_photo"] is False
    assert employee["photo_version"] == 0

    uploaded = client.post(url, files={"file": ("portrait.png", PNG, "text/html")})
    assert uploaded.status_code == 204, uploaded.text
    profile = client.get(f"/api/employees/{employee['id']}").json()
    assert profile["has_photo"] is True
    assert profile["photo_version"] == 1
    assert len(stored_photos()) == 1
    preview = client.get(url)
    assert preview.status_code == 200
    assert preview.content == PNG
    assert preview.headers["content-type"] == "image/png"
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in preview.headers["cache-control"]

    old_path = stored_photos()[0]
    assert client.post(url, files={"file": ("portrait.jpg", JPEG)}).status_code == 204
    assert not old_path.exists()
    assert len(stored_photos()) == 1
    assert stored_photos()[0].read_bytes() == JPEG
    profile = client.get(f"/api/employees/{employee['id']}").json()
    assert profile["photo_version"] == 2

    assert client.delete(url).status_code == 204
    profile = client.get(f"/api/employees/{employee['id']}").json()
    assert profile["has_photo"] is False
    assert profile["photo_version"] == 3
    assert client.get(url).status_code == 404
    assert stored_photos() == []


@pytest.mark.parametrize(
    "name,content,status",
    [
        ("portrait.png", b"", 422),
        ("portrait.png", b"<html>not an image</html>", 422),
        ("portrait.svg", b"<svg></svg>", 422),
        ("portrait.png", PNG + b"x" * (5 * 1024 * 1024), 413),
    ],
)
def test_invalid_profile_photos_leave_no_files(client, employee, name, content, status):
    response = client.post(
        f"/api/employees/{employee['id']}/photo", files={"file": (name, content)}
    )
    assert response.status_code == status, response.text
    assert stored_photos() == []
    assert client.get(f"/api/employees/{employee['id']}").json()["has_photo"] is False


def test_employee_can_change_only_own_profile_photo(client, employee, employee_data):
    other = client.post(
        "/api/employees", json={**employee_data, "email": "other-photo@example.com"}
    ).json()
    client.post(
        "/api/accounts",
        json={
            "username": "photo-owner",
            "password": "Profile-photo-password-2026",
            "role": "employee",
            "employee_id": employee["id"],
            "is_active": True,
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "photo-owner", "password": "Profile-photo-password-2026"},
    )
    assert login.status_code == 200
    own_url = f"/api/employees/{employee['id']}/photo"
    assert client.post(own_url, files={"file": ("portrait.png", PNG)}).status_code == 204
    assert client.get(own_url).status_code == 200
    assert (
        client.post(
            f"/api/employees/{other['id']}/photo", files={"file": ("portrait.png", PNG)}
        ).status_code
        == 404
    )


def test_manager_cannot_change_visible_subordinate_photo(client, employee, employee_data):
    subordinate = client.post(
        "/api/employees", json={**employee_data, "email": "subordinate-photo@example.com"}
    ).json()
    assert (
        client.post(
            f"/api/employees/{subordinate['id']}/photo", files={"file": ("portrait.png", PNG)}
        ).status_code
        == 204
    )
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        manager = session.get(Employee, employee["id"])
        manager.is_manager = True
        report = session.get(Employee, subordinate["id"])
        report.manager_id = manager.id
        session.add(
            Account(
                username="photo-manager",
                password_hash=password_hash("Profile-photo-password-2026"),
                role="manager",
                employee_id=manager.id,
                is_active=True,
            )
        )
        session.commit()
    finally:
        generator.close()
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "photo-manager", "password": "Profile-photo-password-2026"},
        ).status_code
        == 200
    )
    url = f"/api/employees/{subordinate['id']}/photo"
    assert client.get(url).status_code == 200
    assert client.post(url, files={"file": ("portrait.jpg", JPEG)}).status_code == 403
    assert client.delete(url).status_code == 403


def test_deleting_employee_removes_profile_photo(client, employee):
    url = f"/api/employees/{employee['id']}/photo"
    assert client.post(url, files={"file": ("portrait.png", PNG)}).status_code == 204
    assert len(stored_photos()) == 1
    assert client.delete(f"/api/employees/{employee['id']}").status_code == 204
    assert stored_photos() == []


@pytest.mark.parametrize(
    "stored_name",
    ["", ".", "..", "../outside.png", "nested/../inside.png", "file.png:payload", r"C:\file.png"],
)
def test_profile_photo_storage_rejects_traversal(client, stored_name):
    with pytest.raises(NotFoundError, match="Файл не найден"):
        profile_photo_path(stored_name)


def test_missing_profile_photo_file_returns_readable_error(client, employee):
    url = f"/api/employees/{employee['id']}/photo"
    assert client.post(url, files={"file": ("portrait.png", PNG)}).status_code == 204
    Path(stored_photos()[0]).unlink()
    response = client.get(url)
    assert response.status_code == 404
    assert response.json()["detail"] == "Файл фотографии профиля не найден"
    assert client.delete(url).status_code == 204
