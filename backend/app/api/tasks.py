from datetime import date
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import require_assigned_position
from app.db.session import get_db
from app.models.staff import Staff
from app.schemas.task import ChangeRequestCreate, SubmissionCreate
from app.services.tasks import get_task_detail, list_my_tasks, request_task_change, submit_task
from app.core.config import get_settings

router = APIRouter(prefix="/tasks", tags=["tasks"])
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _matches_image_type(content_type: str, content: bytes) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False


@router.get("/today")
def today_tasks(current: Staff = Depends(require_assigned_position), db: Session = Depends(get_db)):
    tasks = list_my_tasks(db, current.id, date.today())
    return [{"id": task.id, "staff_id": task.staff_id, "title": task.template.title, "status": task.status, "due_date": task.due_date} for task in tasks]


@router.get("/{task_id}")
def task_detail(task_id: int, current: Staff = Depends(require_assigned_position), db: Session = Depends(get_db)):
    return get_task_detail(db, task_id, current)


@router.post("/uploads", status_code=201)
async def upload_task_photo(file: UploadFile = File(...), current: Staff = Depends(require_assigned_position)):
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(415, "only JPEG, PNG, and WebP images are allowed")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "image exceeds 5 MB")
    if not content:
        raise HTTPException(422, "empty image")
    if not _matches_image_type(file.content_type or "", content):
        raise HTTPException(415, "image content does not match its declared type")
    digest = sha256(content).hexdigest()[:20]
    key = f"tasks/{current.id}/{uuid4().hex}-{digest}{extension}"
    target = Path(get_settings().upload_dir) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {"key": key, "size": len(content), "content_type": file.content_type}


@router.post("/{task_id}/submissions", status_code=201)
def create_submission(task_id: int, payload: SubmissionCreate, current: Staff = Depends(require_assigned_position), db: Session = Depends(get_db)):
    item = submit_task(db, task_id, current, payload.note, payload.photo_keys)
    return {"id": item.id, "version": item.version, "submitted_at": item.submitted_at}


@router.post("/{task_id}/change-requests", status_code=201)
def create_change_request(task_id: int, payload: ChangeRequestCreate, current: Staff = Depends(require_assigned_position), db: Session = Depends(get_db)):
    item = request_task_change(db, task_id, current, payload.reason)
    return {"id": item.id, "status": item.status}
