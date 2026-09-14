from __future__ import annotations

import os
import shutil
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from app.repositories.base import DataRepository
from app.schemas.models import AppStore


T = TypeVar("T")


class JsonDataRepository(DataRepository):
    """Single-process JSON store with validation, backup and atomic replacement."""

    def __init__(self, path: Path):
        self.path = path
        self.backup_path = path.with_suffix(path.suffix + ".bak")
        self._lock = threading.RLock()

    def exists(self) -> bool:
        return self.path.exists()

    def _load_unlocked(self) -> AppStore:
        if not self.path.exists():
            raise FileNotFoundError(f"데이터 파일이 없습니다: {self.path}")
        return AppStore.model_validate_json(self.path.read_text(encoding="utf-8"))

    def load(self) -> AppStore:
        with self._lock:
            return self._load_unlocked()

    def _save_unlocked(self, store: AppStore) -> None:
        validated = AppStore.model_validate(store)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            shutil.copy2(self.path, self.backup_path)

        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_name = temp_file.name
                temp_file.write(validated.model_dump_json(indent=2))
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def save(self, store: AppStore) -> None:
        with self._lock:
            self._save_unlocked(store)

    def transaction(self, mutate: Callable[[AppStore], T]) -> T:
        with self._lock:
            store = self._load_unlocked()
            result = mutate(store)
            self._save_unlocked(store)
            return result

    def initialize(self, store: AppStore, *, force: bool = False) -> bool:
        with self._lock:
            if self.path.exists() and not force:
                return False
            self._save_unlocked(store)
            return True

