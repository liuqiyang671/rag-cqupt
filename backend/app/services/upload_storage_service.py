import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union
from uuid import uuid4

DEFAULT_UPLOAD_FILENAME = "uploaded-document"
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def save_uploaded_file(filename: Optional[str], data: bytes, upload_dir: Union[str, Path]) -> Path:
    if not data:
        raise ValueError("Uploaded file is empty")

    root = Path(upload_dir).resolve()
    day_dir = root / datetime.now(timezone.utc).strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    stored_path = day_dir / f"{uuid4().hex}_{sanitize_filename(filename)}"
    stored_path.write_bytes(data)
    return stored_path


def delete_uploaded_file(path: Optional[Union[str, Path]]) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def sanitize_filename(filename: Optional[str]) -> str:
    original = Path(filename or DEFAULT_UPLOAD_FILENAME).name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", original).strip(" .")
    if not cleaned:
        cleaned = DEFAULT_UPLOAD_FILENAME

    stem = Path(cleaned).stem.upper()
    if stem in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"

    return _limit_filename_length(cleaned)


def _limit_filename_length(filename: str, max_length: int = 180) -> str:
    if len(filename) <= max_length:
        return filename

    path = Path(filename)
    suffix = path.suffix
    stem_limit = max(1, max_length - len(suffix))
    return f"{path.stem[:stem_limit]}{suffix}"
