from pathlib import Path

import pytest

from app.config import get_settings
from app.errors import NotFoundError
from app.services import certificates
from app.storage import certificate_path as storage_path

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"


@pytest.fixture
def certificate_path(client, employee, skill):
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    assert client.put(path, json={"current_level": None, "target_level": 3}).status_code == 200
    return f"{path}/certificates"


def stored_files():
    return list((get_settings().media_root / "certificates").glob("*"))


def test_multiple_certificates_persist_in_profile_and_matrix(client, employee, certificate_path):
    first = client.post(
        certificate_path,
        data={"title": "  Python Foundation  "},
        files={"file": ("сертификат.pdf", PDF, "application/pdf")},
    )
    assert first.status_code == 201, first.text
    second = client.post(certificate_path, files={"file": ("сертификат.pdf", PDF)})
    assert second.status_code == 201
    assert first.json()["title"] == "Python Foundation"
    assert second.json()["title"] == "сертификат.pdf"
    assert first.json()["size"] == len(PDF)
    assert first.json()["content_type"] == "application/pdf"
    assert "stored_name" not in first.json()
    assert len(stored_files()) == 2
    assert all(file.read_bytes() == PDF for file in stored_files())
    profile = client.get(f"/api/employees/{employee['id']}").json()
    matrix = client.get("/api/matrix").json()
    expected = [second.json(), first.json()]
    assert profile["skills"][0]["certificates"] == expected
    assert matrix["employees"][0]["skills"][0]["certificates"] == expected
    assert client.get(certificate_path).json() == expected


def test_preview_download_and_delete(client, certificate_path):
    certificate = client.post(certificate_path, files={"file": ("сертификат.pdf", PDF)}).json()
    url = f"{certificate_path}/{certificate['id']}/file"
    preview = client.get(url)
    assert preview.status_code == 200
    assert preview.content == PDF
    assert preview.headers["content-type"] == "application/pdf"
    assert preview.headers["content-disposition"].startswith("inline;")
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in preview.headers["content-security-policy"]
    assert "filename*=utf-8''" in preview.headers["content-disposition"]
    assert (
        client.get(f"{url}?download=true").headers["content-disposition"].startswith("attachment;")
    )
    assert client.delete(f"{certificate_path}/{certificate['id']}").status_code == 204
    assert client.get(url).status_code == 404
    assert client.get(certificate_path).json() == []
    assert stored_files() == []


@pytest.mark.parametrize("delete_skill", [True, False])
def test_parent_deletion_removes_records_and_files(
    client, employee, certificate_path, delete_skill
):
    client.post(certificate_path, files={"file": ("certificate.pdf", PDF)})
    parent_url = (
        certificate_path.removesuffix("/certificates")
        if delete_skill
        else f"/api/employees/{employee['id']}"
    )
    assert client.delete(parent_url).status_code == 204
    assert client.get(certificate_path).status_code == 404
    assert stored_files() == []


@pytest.mark.parametrize(
    "name,content,status",
    [
        ("certificate.pdf", b"", 422),
        ("certificate.pdf", b"<html>malformed</html>", 422),
        ("certificate.png", PDF, 422),
        ("certificate.html", b"<html></html>", 422),
        ("certificate.exe", b"MZ", 422),
        ("certificate.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024), 413),
    ],
    ids=["empty", "fake-pdf", "wrong-format", "html", "executable", "oversized"],
)
def test_invalid_uploads_leave_no_records_or_files(client, certificate_path, name, content, status):
    response = client.post(certificate_path, files={"file": (name, content)})
    assert response.status_code == status, response.text
    assert client.get(certificate_path).json() == []
    assert stored_files() == []


@pytest.mark.parametrize(
    "name,content,content_type",
    [
        ("certificate.PNG", b"\x89PNG\r\n\x1a\n" + b"sample", "image/png"),
        ("certificate.jpg", b"\xff\xd8\xff" + b"sample", "image/jpeg"),
        ("certificate.jpeg", b"\xff\xd8\xff" + b"sample", "image/jpeg"),
        ("certificate.webp", b"RIFF\x00\x00\x00\x00WEBPsample", "image/webp"),
    ],
)
def test_image_types_are_detected_without_trusting_client_mime(
    client, certificate_path, name, content, content_type
):
    response = client.post(certificate_path, files={"file": (name, content, "text/html")})
    assert response.status_code == 201
    certificate = response.json()
    assert certificate["content_type"] == content_type
    assert client.get(f"{certificate_path}/{certificate['id']}/file").content == content


def test_upload_requires_existing_employee_skill(client, employee, skill):
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}/certificates"
    assert client.post(path, files={"file": ("cert.pdf", PDF)}).status_code == 404
    assert (
        client.post(
            "/api/employees/999/skills/999/certificates", files={"file": ("cert.pdf", PDF)}
        ).status_code
        == 404
    )
    assert stored_files() == []


def test_certificate_is_scoped_to_employee_and_skill(
    client, employee, employee_data, skill, certificate_path
):
    certificate = client.post(certificate_path, files={"file": ("cert.pdf", PDF)}).json()
    other = client.post(
        "/api/employees", json={**employee_data, "email": "other@example.com"}
    ).json()
    other_path = f"/api/employees/{other['id']}/skills/{skill['id']}"
    client.put(other_path, json={"current_level": None, "target_level": 3})
    wrong_url = f"{other_path}/certificates/{certificate['id']}"
    assert client.get(f"{wrong_url}/file").status_code == 404
    assert client.delete(wrong_url).status_code == 404
    assert len(stored_files()) == 1


def test_original_name_cannot_control_storage_path(client, certificate_path):
    response = client.post(certificate_path, files={"file": ("../../outside.pdf", PDF)})
    assert response.status_code == 201
    assert response.json()["original_name"] == "outside.pdf"
    file = stored_files()[0]
    assert file.parent == get_settings().media_root / "certificates"
    assert file.name != "outside.pdf"
    with pytest.raises(NotFoundError, match="Файл не найден"):
        storage_path("../outside.pdf")


@pytest.mark.parametrize(
    "stored_name",
    ["", ".", "..", "../outside.pdf", "nested/../inside.pdf", "file.pdf:payload", r"C:\file.pdf"],
)
def test_storage_rejects_traversal_and_windows_stream_names(client, stored_name):
    with pytest.raises(NotFoundError, match="Файл не найден"):
        storage_path(stored_name)


def test_failed_commit_cleans_up_upload(client, certificate_path, monkeypatch):
    def fail_commit(*_):
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(certificates, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="Simulated database failure"):
        client.post(certificate_path, files={"file": ("cert.pdf", PDF)})
    assert stored_files() == []
    assert client.get(certificate_path).json() == []


def test_missing_file_returns_readable_error(client, certificate_path):
    certificate = client.post(certificate_path, files={"file": ("cert.pdf", PDF)}).json()
    Path(stored_files()[0]).unlink()
    response = client.get(f"{certificate_path}/{certificate['id']}/file")
    assert response.status_code == 404
    assert response.json()["detail"] == "Файл сертификата не найден"
    assert client.delete(f"{certificate_path}/{certificate['id']}").status_code == 204
