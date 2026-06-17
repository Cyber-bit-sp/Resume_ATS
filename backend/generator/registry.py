import shutil
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify


def _resume_folder_name(generation):
    title = getattr(getattr(generation, "resume", None), "title", "")
    fallback = f"resume-{getattr(generation, 'id', 'generated')}"
    return slugify((title or "").strip()) or fallback


def resume_registry_dir(generation):
    return Path(settings.BASE_DIR).parent / "resume" / _resume_folder_name(generation)


def requested_resume_dir(folder):
    folder = str(folder or "").strip()
    if not folder:
        return None
    target_dir = Path(folder).expanduser()
    if not target_dir.is_absolute():
        target_dir = Path(settings.BASE_DIR).parent / target_dir
    return target_dir


def _target_dir(generation, folder=None):
    return requested_resume_dir(folder) or resume_registry_dir(generation)


def save_bytes_to_resume_registry(generation, filename, content, folder=None):
    target_dir = _target_dir(generation, folder)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    target_path.write_bytes(content)
    return target_path


def save_file_to_resume_registry(generation, filename, source_file, folder=None):
    target_dir = _target_dir(generation, folder)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    with target_path.open("wb") as output:
        shutil.copyfileobj(source_file, output)
    return target_path


def registry_response_payload(path):
    project_root = Path(settings.BASE_DIR).parent
    try:
        relative_path = path.relative_to(project_root)
    except ValueError:
        relative_path = path
    return {
        "detail": "Saved to resume registry.",
        "path": str(relative_path).replace("\\", "/"),
    }
