from dataclasses import dataclass
from typing import Generic, TypeVar


ItemType = TypeVar("ItemType")


@dataclass(frozen=True)
class PaginationParams:
    skip: int = 0
    limit: int = 20


@dataclass(frozen=True)
class Page(Generic[ItemType]):
    items: list[ItemType]
    total: int
    skip: int
    limit: int

    @property
    def returned(self) -> int:
        return len(self.items)

    @property
    def has_next(self) -> bool:
        return self.skip + self.returned < self.total

    @property
    def has_previous(self) -> bool:
        return self.skip > 0
