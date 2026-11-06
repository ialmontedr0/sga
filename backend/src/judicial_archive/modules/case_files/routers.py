from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, SortOrder, pagination_params
from judicial_archive.modules.case_files import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/case-files", tags=["Expedientes"])
persons_router = APIRouter(prefix="/persons", tags=["Personas"])


@router.get("/duplicates", response_model=list[schemas.DuplicateCaseFileOut])
async def list_case_file_duplicates(
    court_id: UUID,
    nuc: Annotated[str, Query(min_length=1, max_length=100)],
    year: int,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> list[schemas.DuplicateCaseFileOut]:
    return await services.list_case_file_duplicates(
        session,
        court_id=court_id,
        nuc=nuc,
        year=year,
        limit=limit,
    )


@router.get("", response_model=Page[schemas.CaseFileOut])
async def list_case_files(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    court_id: UUID | None = None,
    box_id: UUID | None = None,
    year: int | None = None,
    lifecycle_status: str | None = None,
    verification_status: str | None = None,
    sort_by: str = "created_at",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> Page[schemas.CaseFileOut]:
    return await services.list_case_files(
        session,
        params=params,
        q=q,
        court_id=court_id,
        box_id=box_id,
        year=year,
        lifecycle_status=lifecycle_status,
        verification_status=verification_status,
        sort_by=sort_by,
        order=order,
    )


@router.post("", response_model=schemas.CaseFileDetailOut)
async def create_case_file(
    request: Request,
    body: schemas.CaseFileCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_CREATE)),
) -> schemas.CaseFileDetailOut:
    return await services.create_case_file(request, session, current_user, body)


@router.get("/{case_file_id}", response_model=schemas.CaseFileDetailOut)
async def get_case_file(
    case_file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> schemas.CaseFileDetailOut:
    return await services.get_case_file(session, case_file_id)


@router.patch("/{case_file_id}", response_model=schemas.CaseFileDetailOut)
async def update_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.update_case_file(request, session, current_user, case_file_id, body)


@router.post("/{case_file_id}/relocate", response_model=schemas.CaseFileDetailOut)
async def relocate_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileRelocate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.relocate_case_file(request, session, current_user, case_file_id, body)


@router.post(
    "/{case_file_id}/identifiers/correct",
    response_model=schemas.CaseFileDetailOut,
)
async def correct_case_identifier(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileIdentifierCorrection,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.correct_identifier(request, session, current_user, case_file_id, body)


@router.post("/{case_file_id}/archive", response_model=schemas.CaseFileDetailOut)
async def archive_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.archive_case_file(request, session, current_user, case_file_id, body)


@router.post("/{case_file_id}/void", response_model=schemas.CaseFileDetailOut)
async def void_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.void_case_file(request, session, current_user, case_file_id, body)


@router.delete("/{case_file_id}", status_code=204)
async def delete_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileDeleteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> Response:
    await services.soft_delete_case_file(request, session, current_user, case_file_id, body)
    return Response(status_code=204)


@router.get("/{case_file_id}/parties", response_model=list[schemas.CasePartyOut])
async def list_case_parties(
    case_file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> list[schemas.CasePartyOut]:
    detail = await services.get_case_file_detail(session, case_file_id)
    return detail.parties


@router.post("/{case_file_id}/parties", response_model=schemas.CasePartyOut)
async def add_case_party(
    request: Request,
    case_file_id: UUID,
    body: schemas.CasePartyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CasePartyOut:
    return await services.add_party(request, session, current_user, case_file_id, body)


@router.post(
    "/{case_file_id}/parties/with-person",
    response_model=schemas.CasePartyOut,
)
async def add_case_party_with_person(
    request: Request,
    case_file_id: UUID,
    body: schemas.CasePartyWithPersonCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CasePartyOut:
    return await services.add_party_with_person(request, session, current_user, case_file_id, body)


@router.delete("/{case_file_id}/parties/{party_id}", status_code=204)
async def remove_case_party(
    request: Request,
    case_file_id: UUID,
    party_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> Response:
    await services.remove_party(request, session, current_user, case_file_id, party_id)
    return Response(status_code=204)


@persons_router.get("/duplicates", response_model=list[schemas.DuplicatePersonOut])
async def list_person_duplicates(
    display_name: Annotated[str, Query(min_length=1, max_length=300)],
    identification_number: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> list[schemas.DuplicatePersonOut]:
    return await services.list_person_duplicates(
        session,
        display_name=display_name,
        identification_number=identification_number,
        limit=limit,
    )


@persons_router.get("", response_model=Page[schemas.PersonOut])
async def list_persons(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    identification_number: Annotated[str | None, Query(max_length=64)] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> Page[schemas.PersonOut]:
    return await services.list_persons(
        session,
        params=params,
        q=q,
        identification_number=identification_number,
    )


@persons_router.get("/{person_id}", response_model=schemas.PersonOut)
async def get_person(
    person_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> schemas.PersonOut:
    return await services.get_person(session, person_id)
