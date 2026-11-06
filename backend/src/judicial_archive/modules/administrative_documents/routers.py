from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import Page, PageParams, SortOrder, pagination_params
from judicial_archive.modules.administrative_documents import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(
    prefix="/administrative-documents",
    tags=["Documentos administrativos"],
)


@router.get("/duplicates", response_model=list[schemas.DuplicateAdministrativeDocumentOut])
async def list_document_duplicates(
    box_id: UUID,
    title: Annotated[str, Query(min_length=1, max_length=300)],
    document_year: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_READ)),
) -> list[schemas.DuplicateAdministrativeDocumentOut]:
    return await services.list_administrative_document_duplicates(
        session,
        box_id=box_id,
        title=title,
        document_year=document_year,
    )


@router.get("", response_model=Page[schemas.AdministrativeDocumentOut])
async def list_administrative_documents(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    box_id: UUID | None = None,
    document_year: int | None = None,
    lifecycle_status: str | None = None,
    sort_by: str = "created_at",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_READ)),
) -> Page[schemas.AdministrativeDocumentOut]:
    return await services.list_administrative_documents(
        session,
        params=params,
        q=q,
        box_id=box_id,
        document_year=document_year,
        lifecycle_status=lifecycle_status,
        sort_by=sort_by,
        order=order,
    )


@router.post("", response_model=schemas.AdministrativeDocumentOut)
async def create_administrative_document(
    request: Request,
    body: schemas.AdministrativeDocumentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.create_administrative_document(request, session, current_user, body)


@router.get("/{document_id}", response_model=schemas.AdministrativeDocumentOut)
async def get_administrative_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_READ)),
) -> schemas.AdministrativeDocumentOut:
    return await services.get_administrative_document(session, document_id)


@router.patch("/{document_id}", response_model=schemas.AdministrativeDocumentOut)
async def update_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.update_administrative_document(
        request, session, current_user, document_id, body
    )


@router.post(
    "/{document_id}/archive",
    response_model=schemas.AdministrativeDocumentOut,
)
async def archive_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.set_administrative_document_lifecycle(
        request,
        session,
        current_user,
        document_id,
        target="ARCHIVED",
        body=body,
    )


@router.post(
    "/{document_id}/void",
    response_model=schemas.AdministrativeDocumentOut,
)
async def void_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.set_administrative_document_lifecycle(
        request,
        session,
        current_user,
        document_id,
        target="VOIDED",
        body=body,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentDeleteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> Response:
    await services.soft_delete_administrative_document(
        request, session, current_user, document_id, body
    )
    return Response(status_code=204)
