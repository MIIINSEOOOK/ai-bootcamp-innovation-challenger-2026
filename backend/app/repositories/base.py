from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

from app.schemas.models import AppStore


T = TypeVar("T")


class DataRepository(ABC):
    """Persistence boundary; replace this implementation when moving to a DB."""

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def load(self) -> AppStore:
        raise NotImplementedError

    @abstractmethod
    def save(self, store: AppStore) -> None:
        raise NotImplementedError

    @abstractmethod
    def transaction(self, mutate: Callable[[AppStore], T]) -> T:
        raise NotImplementedError

    @abstractmethod
    def initialize(self, store: AppStore, *, force: bool = False) -> bool:
        raise NotImplementedError

