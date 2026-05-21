"""File attachments via Emergent Object Storage."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response

from core import (
    db, now_utc, audit, get_current_user, require_roles, load_case_for_user,
    ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_RECEPTION, ROLE_ADMIN,
)
from storage import put_object, get_object, ALLOWED_EXTS, MIME_TYPES, MAX_BYTES, APP_NAME

router = APIRouter()


@router.post("/cases/{case_id}/attachments")
async def upload_attachment(
    case_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_RECEPTION, ROLE_ADMIN)),
):
    c = await load_case_for_user(case_id, user)
    fname = file.filename or "upload"
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Only {sorted(ALLOWED_EXTS)} allowed")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")
    content_type = MIME_TYPES[ext]
    patient_uid = (await db.patients.find_one({"id": c["patient_id"]}, {"patient_uid": 1, "_id": 0})) or {}
    path = f"{APP_NAME}/attachments/{patient_uid.get('patient_uid', 'unknown')}/{case_id}/{uuid.uuid4()}.{ext}"
    try:
        result = put_object(path, data, content_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {e}")
    record = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "patient_id": c["patient_id"],
        "storage_path": result.get("path") or path,
        "original_filename": fname,
        "content_type": content_type,
        "size_bytes": len(data),
        "uploaded_by": user["id"],
        "uploaded_by_name": user.get("name"),
        "is_deleted": False,
        "created_at": now_utc().isoformat(),
    }
    await db.attachments.insert_one(record)
    record.pop("_id", None)
    await audit(user, "ATTACHMENT_UPLOAD", "Attachment", record["id"], {"filename": fname, "size": len(data)})
    return {"attachment": record}


@router.get("/cases/{case_id}/attachments")
async def list_attachments(case_id: str, user: dict = Depends(get_current_user)):
    await load_case_for_user(case_id, user)
    files = await db.attachments.find(
        {"case_id": case_id, "is_deleted": False}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"attachments": files}


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: str, user: dict = Depends(get_current_user)):
    rec = await db.attachments.find_one({"id": attachment_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    await load_case_for_user(rec["case_id"], user)  # access check
    try:
        data, ctype = get_object(rec["storage_path"])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Storage error: {e}")
    await audit(user, "ATTACHMENT_DOWNLOAD", "Attachment", attachment_id)
    return Response(
        content=data,
        media_type=rec.get("content_type") or ctype,
        headers={"Content-Disposition": f'inline; filename="{rec["original_filename"]}"'},
    )


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    rec = await db.attachments.find_one({"id": attachment_id, "is_deleted": False})
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    await load_case_for_user(rec["case_id"], user)
    await db.attachments.update_one(
        {"id": attachment_id},
        {"$set": {"is_deleted": True, "deleted_at": now_utc().isoformat(), "deleted_by": user["id"]}},
    )
    await audit(user, "ATTACHMENT_DELETE", "Attachment", attachment_id)
    return {"ok": True}
