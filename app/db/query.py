from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Literal


SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True)
class SortParams:
    sort_by: str = "created_at"
    sort_order: SortDirection = "desc"

    def apply(self, column: Any) -> Any:
        if self.sort_order == "asc":
            return column.asc()
        return column.desc()

    def resolve(self, columns: Mapping[str, Any]) -> Any:
        try:
            column = columns[self.sort_by]
        except KeyError as exc:
            raise ValueError(f"Unsupported sort field: {self.sort_by}") from exc
        return self.apply(column)
