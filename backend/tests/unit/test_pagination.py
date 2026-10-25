from __future__ import annotations

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.core.pagination import (
    MAX_PAGE_SIZE,
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
)


def test_page_params_offset_and_limit() -> None:
    params = PageParams(page=3, page_size=25)

    assert params.offset == 50
    assert params.limit == 25


def test_page_build_with_results() -> None:
    params = PageParams(page=2, page_size=10)

    page = Page[int].build([1, 2, 3], total=23, params=params)

    assert page.items == [1, 2, 3]
    assert page.total == 23
    assert page.pages == 3
    assert page.has_next is True
    assert page.has_previous is True


def test_page_build_empty() -> None:
    params = PageParams(page=1, page_size=MAX_PAGE_SIZE)

    page = Page[int].build([], total=0, params=params)

    assert page.pages == 0
    assert page.has_next is False
    assert page.has_previous is False


def test_sort_field_must_be_allowed() -> None:
    with pytest.raises(InvalidParameterError):
        build_sort_params("password", SortOrder.ASC, allowed_fields=frozenset({"number"}))


def test_sort_field_allowed() -> None:
    params = build_sort_params("number", SortOrder.DESC, allowed_fields=frozenset({"number"}))

    assert params.sort_by == "number"
    assert params.order is SortOrder.DESC
