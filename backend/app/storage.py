"""Certificate filesystem adapter; filenames from users never become storage paths."""

from pathlib import Path

from app.config import get_settings
from app.errors import NotFoundError


def certificate_path(stored_name: str) -> Path:
    return stored_file_path("certificates", stored_name)


def profile_photo_path(stored_name: str) -> Path:
    return stored_file_path("profile-photos", stored_name)


def stored_file_path(directory_name: str, stored_name: str) -> Path:
    directory = (get_settings().media_root / directory_name).resolve()
    # Reject path syntax explicitly, including Windows alternate data streams.
    if not stored_name or stored_name in {".", ".."} or any(c in stored_name for c in "/\\:"):
        raise NotFoundError("Файл не найден")
    path = (directory / stored_name).resolve()
    if path.parent != directory:
        raise NotFoundError("Файл не найден")
    return path


def remove_files(stored_names: list[str]) -> None:
    for name in stored_names:
        certificate_path(name).unlink(missing_ok=True)


def remove_profile_photo(stored_name: str | None) -> None:
    if stored_name:
        profile_photo_path(stored_name).unlink(missing_ok=True)
