import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_json_revision(data) -> str:
    payload = canonical_json(data).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_write_text(file_path: Path, text: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=f".{file_path.name}.", suffix=".tmp", dir=file_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            temp_file.write(text)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, file_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def atomic_write_json(file_path: Path, data, *, indent: int = 2):
    text = json.dumps(data, ensure_ascii=False, indent=indent)
    atomic_write_text(file_path, text)


@contextmanager
def file_lock(file_path: Path):
    lock_path = file_path.with_suffix(file_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        lock_file.seek(0)
        if os.name == "nt":
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
