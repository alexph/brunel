from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoreKey:
    kind: str
    id: str


@dataclass(frozen=True)
class StoreChange:
    updated: tuple[str, ...] = ()
    structure: bool = False
    status: bool = False


class Store(Protocol):
    def apply(self, event: object) -> StoreChange: ...


class StoreRouter:
    def __init__(self):
        self._stores: dict[StoreKey, Store] = {}

    def register(self, key: StoreKey, store: Store) -> None:
        if key in self._stores:
            raise ValueError(f"Store already registered: {key}")
        self._stores[key] = store

    def get(self, key: StoreKey) -> Store:
        return self._stores[key]

    def dispatch(self, key: StoreKey, event: object) -> StoreChange:
        return self.get(key).apply(event)
