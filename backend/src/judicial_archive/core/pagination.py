from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

from judicial_archive.core.errors import InvalidParameterError

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: Annotated[int, Query(ge=1, description="Numero de pagina (empieza en 1).")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Elementos por pagina."),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class SortParams(BaseModel):
    sort_by: str | None = None
    order: SortOrder = SortOrder.ASC


def build_sort_params(
    sort_by: str | None,
    order: SortOrder,
    *,
    allowed_fields: frozenset[str],
) -> SortParams:
    if sort_by is not None and sort_by not in allowed_fields:
        raise InvalidParameterError(
            "El campo de ordenamiento no esta permitido.",
            details={"allowed_fields": sorted(allowed_fields)},
        )
    return SortParams(sort_by=sort_by, order=order)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool

    @classmethod
    def build(cls, items: Sequence[T], *, total: int, params: PageParams) -> Page[T]:
        pages = ceil(total / params.page_size) if total > 0 else 0
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
            has_next=params.page < pages,
            has_previous=params.page > 1 and total > 0,
        )


## Ejemplo de uso en un endpoint

""" from typing import Annotated

from fastapi import APIRouter, Depends, Query

from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)

router = APIRouter()

_ALLOWED_SORT_FIELDS = frozenset({"number", "created_at"})


@router.get("/boxes", response_model=Page[dict[str, object]])
async def list_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    sort_by: Annotated[str | None, Query()] = None,
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
) -> Page[dict[str, object]]:
    build_sort_params(sort_by, order, allowed_fields=_ALLOWED_SORT_FIELDS)
    # La consulta real se implementa en B6/B8.
    return Page[dict[str, object]].build([], total=0, params=params) """
