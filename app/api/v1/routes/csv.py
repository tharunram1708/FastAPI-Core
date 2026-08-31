import csv
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.schemas.enterprise import CSVImportResponse
from app.schemas.item import ItemCreate, ItemRead


router = APIRouter()


@router.post("/items/import", response_model=CSVImportResponse, summary="Import items from CSV")
async def import_items_csv(
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.IMPORT_CSV))],
    file: UploadFile = File(...),
) -> CSVImportResponse:
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    inserted = 0
    errors: list[dict] = []
    for row_number, row in enumerate(reader, start=2):
        try:
            payload = ItemCreate(
                name=row.get("name") or "",
                description=row.get("description") or None,
                category=row.get("category") or "general",
                is_active=(row.get("is_active") or "true").casefold() == "true",
                inventory_count=int(row.get("inventory_count") or 0),
            )
            item = db.items.create_item(payload)
            db.enterprise.create_audit_log(
                actor_id=current_user.id,
                action="CSV_IMPORT_ITEM",
                resource_type="item",
                resource_id=str(item.id),
            )
            inserted += 1
        except Exception as exc:
            errors.append({"row": row_number, "error": str(exc)})
    return CSVImportResponse(inserted=inserted, errors=errors)


@router.get("/items/export", summary="Export items to CSV")
async def export_items_csv(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.EXPORT_CSV))],
    q: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
) -> StreamingResponse:
    rows = db.items.list_items(q=q, categories=[category] if category else None, is_active=is_active, limit=1000)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "name", "description", "category", "is_active", "inventory_count", "rating"])
    for item in rows:
        writer.writerow([
            item.id,
            item.name,
            item.description or "",
            item.category,
            item.is_active,
            item.inventory_count,
            item.rating if item.rating is not None else "",
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=items.csv"},
    )
