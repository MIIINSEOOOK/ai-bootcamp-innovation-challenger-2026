from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.repositories.json_repository import JsonDataRepository
from app.schemas.models import AppStore


def test_repository_creates_backup_and_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "store.json"
    repository = JsonDataRepository(path)
    repository.initialize(AppStore(schemaVersion=1))
    repository.save(AppStore(schemaVersion=1))
    assert path.exists()
    assert path.with_suffix(".json.bak").exists()
    assert repository.load().schemaVersion == 1


def test_failed_atomic_replace_keeps_original(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "store.json"
    repository = JsonDataRepository(path)
    repository.initialize(AppStore(schemaVersion=1))
    original = path.read_text(encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError):
        repository.save(AppStore(schemaVersion=2))
    assert path.read_text(encoding="utf-8") == original

