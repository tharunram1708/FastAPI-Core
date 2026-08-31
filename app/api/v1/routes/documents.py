from hashlib import sha256
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Path as RoutePath, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.core.config import BASE_DIR, settings
from app.core.exceptions import DocumentNotFoundError
from app.schemas.enterprise import DocumentRead, DocumentUpdate


router = APIRouter()


def _upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    if not root.is_absolute():
        root = BASE_DIR / root
    root.mkdir(parents=True, exist_ok=True)
    return root


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document",
)
async def upload_document(
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
) -> DocumentRead:
    content = await file.read()
    checksum = sha256(content).hexdigest()
    stored_name = f"{checksum[:16]}-{file.filename}"
    storage_path = _upload_root() / stored_name
    storage_path.write_bytes(content)
    document = db.enterprise.documents.create(
        {
            "owner_id": current_user.id,
            "filename": file.filename or stored_name,
            "content_type": file.content_type or "application/octet-stream",
            "storage_path": str(storage_path),
            "size_bytes": len(content),
            "checksum": checksum,
            "description": description,
        }
    )
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="UPLOAD_DOCUMENT",
        resource_type="document",
        resource_id=str(document.id),
    )
    return document


@router.get("", response_model=list[DocumentRead], summary="List documents")
async def list_documents(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    skip: int = 0,
    limit: int = 100,
) -> list[DocumentRead]:
    return db.enterprise.documents.list(skip=skip, limit=limit)


@router.get("/{document_id}", response_model=DocumentRead, summary="Get document metadata")
async def get_document(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    document_id: Annotated[UUID, RoutePath(description="Document identifier.")],
) -> DocumentRead:
    document = db.enterprise.documents.get(document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError()
    return document


@router.get("/{document_id}/download", summary="Download document")
async def download_document(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    document_id: Annotated[UUID, RoutePath(description="Document identifier.")],
) -> FileResponse:
    document = db.enterprise.documents.get(document_id)
    if document is None or document.deleted_at is not None or not Path(document.storage_path).exists():
        raise DocumentNotFoundError()
    return FileResponse(
        document.storage_path,
        media_type=document.content_type,
        filename=document.filename,
    )


@router.patch("/{document_id}", response_model=DocumentRead, summary="Update document")
async def update_document(
    payload: DocumentUpdate,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    document_id: Annotated[UUID, RoutePath(description="Document identifier.")],
) -> DocumentRead:
    document = db.enterprise.documents.get(document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError()
    db.enterprise.documents.update(document, payload.model_dump(exclude_unset=True))
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="UPDATE_DOCUMENT",
        resource_type="document",
        resource_id=str(document.id),
    )
    return document


@router.put("/{document_id}/file", response_model=DocumentRead, summary="Replace document file")
async def replace_document_file(
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    document_id: Annotated[UUID, RoutePath(description="Document identifier.")],
    file: UploadFile = File(...),
) -> DocumentRead:
    document = db.enterprise.documents.get(document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError()
    content = await file.read()
    checksum = sha256(content).hexdigest()
    storage_path = _upload_root() / f"{checksum[:16]}-{file.filename}"
    storage_path.write_bytes(content)
    old_path = Path(document.storage_path)
    if old_path.exists():
        old_path.unlink()
    db.enterprise.documents.update(
        document,
        {
            "filename": file.filename or document.filename,
            "content_type": file.content_type or "application/octet-stream",
            "storage_path": str(storage_path),
            "size_bytes": len(content),
            "checksum": checksum,
        },
    )
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="REPLACE_DOCUMENT_FILE",
        resource_type="document",
        resource_id=str(document.id),
    )
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete document")
async def delete_document(
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_FILES))],
    document_id: Annotated[UUID, RoutePath(description="Document identifier.")],
) -> Response:
    document = db.enterprise.documents.get(document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError()
    db.enterprise.documents.soft_delete(document)
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="DELETE_DOCUMENT",
        resource_type="document",
        resource_id=str(document.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
