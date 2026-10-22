from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.enums import EmploymentStatus, Frequency, PositionCode, PublicationStatus, ReviewStatus, Role, TaskStatus
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.staff import Position, Staff, WorkCalendar
from app.models.task import ChangeRequest, TaskInstance, TaskTemplate
from app.schemas.admin import CalendarUpdate, KnowledgeChunkUpdate, StaffCreate, StaffPositionUpdate, TaskTemplateCreate, TaskTemplateUpdate
from app.schemas.task import ChangeReview
from app.services.generation import generate_tasks_for_date
from app.services.tasks import review_change_request
from app.services.imports import import_workbook
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(_: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    today = date.today()
    active_staff = db.scalar(select(func.count(Staff.id)).where(Staff.employment_status == EmploymentStatus.ACTIVE)) or 0
    today_tasks = db.scalar(select(func.count(TaskInstance.id)).where(TaskInstance.due_date == today)) or 0
    overdue_tasks = db.scalar(select(func.count(TaskInstance.id)).where(
        TaskInstance.status == TaskStatus.PENDING,
        (TaskInstance.due_date < today) | ((TaskInstance.due_at.is_not(None)) & (TaskInstance.due_at < datetime.now())),
    )) or 0
    pending_change_requests = db.scalar(select(func.count(ChangeRequest.id)).where(ChangeRequest.status == ReviewStatus.PENDING)) or 0
    draft_chunks = db.scalar(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.publish_status == PublicationStatus.DRAFT)) or 0
    return {"active_staff": active_staff, "today_tasks": today_tasks, "overdue_tasks": overdue_tasks, "pending_change_requests": pending_change_requests, "draft_chunks": draft_chunks}


@router.get("/change-requests")
def list_pending_change_requests(_: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    requests = db.scalars(
        select(ChangeRequest)
        .where(ChangeRequest.status == ReviewStatus.PENDING)
        .order_by(ChangeRequest.id)
    ).all()
    result = []
    for item in requests:
        task = db.get(TaskInstance, item.task_instance_id)
        requester = db.get(Staff, item.requester_id)
        if task is None or requester is None:
            continue
        result.append({
            "id": item.id,
            "task_id": task.id,
            "task_title": task.template.title,
            "requester_id": requester.id,
            "requester_name": requester.name,
            "position_code": requester.position.code if requester.position else None,
            "reason": item.reason,
            "status": item.status,
        })
    return result


@router.get("/staff")
def list_staff(_: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": staff.id, "name": staff.name, "employee_no": staff.employee_no, "role": staff.role, "position": staff.position.code if staff.position else None, "employment_status": staff.employment_status, "has_password": bool(staff.password_hash)} for staff in db.scalars(select(Staff))]


@router.post("/staff", status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreate, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    if payload.role is Role.ADMIN and payload.position_code is not None:
        raise HTTPException(422, "administrator cannot be assigned an employee position")
    position = db.scalar(select(Position).where(Position.code == payload.position_code)) if payload.position_code else None
    if payload.position_code and position is None:
        raise HTTPException(422, "unknown position")
    if position and payload.role is Role.EMPLOYEE:
        active_count = db.scalar(select(Staff.id).where(Staff.position_id == position.id, Staff.employment_status == EmploymentStatus.ACTIVE).limit(1))
        if active_count:
            raise HTTPException(409, "this position already has an active employee")
    staff = Staff(name=payload.name.strip(), employee_no=payload.employee_no.strip(), phone=payload.phone, password_hash=hash_password(payload.password), position_id=position.id if position else None, role=payload.role, employment_status=EmploymentStatus.ACTIVE)
    db.add(staff)
    try:
        db.flush()
    except Exception as error:
        db.rollback()
        raise HTTPException(409, "employee number or phone already exists") from error
    db.add(AuditLog(actor_id=current.id, action="staff.create", resource_type="staff", resource_id=str(staff.id)))
    db.commit()
    return {"id": staff.id, "name": staff.name, "employee_no": staff.employee_no, "role": staff.role, "position": payload.position_code, "has_password": True}


@router.patch("/staff/{staff_id}/position")
def assign_staff_position(staff_id: int, payload: StaffPositionUpdate, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    staff = db.get(Staff, staff_id)
    if staff is None or staff.role is not Role.EMPLOYEE:
        raise HTTPException(404, "employee not found")
    position = db.scalar(select(Position).where(Position.code == payload.position_code))
    if position is None:
        raise HTTPException(422, "unknown position")
    occupied = db.scalar(select(Staff.id).where(Staff.id != staff.id, Staff.position_id == position.id, Staff.employment_status == EmploymentStatus.ACTIVE).limit(1))
    if occupied:
        raise HTTPException(409, "this position already has an active employee")
    staff.position_id = position.id
    db.add(AuditLog(actor_id=current.id, action="staff.position_assign", resource_type="staff", resource_id=str(staff.id)))
    db.commit()
    return {"id": staff.id, "position": position.code}


@router.get("/task-templates")
def list_templates(_: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    templates = db.scalars(select(TaskTemplate).order_by(TaskTemplate.position_code, TaskTemplate.id)).all()
    return [{"id": item.id, "position_code": item.position_code, "title": item.title, "frequency": item.frequency, "schedule_rule": item.schedule_rule, "time_range": item.time_range, "due_time": item.due_time, "content": item.content, "acceptance_criteria": item.acceptance_criteria, "status": item.status, "source_sheet": item.source_sheet, "source_row": item.source_row} for item in templates]


@router.post("/task-templates", status_code=status.HTTP_201_CREATED)
def create_template(payload: TaskTemplateCreate, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    template = TaskTemplate(**payload.model_dump(), status=PublicationStatus.DRAFT)
    db.add(template)
    db.flush()
    db.add(AuditLog(actor_id=current.id, action="task_template.create", resource_type="task_template", resource_id=str(template.id)))
    db.commit()
    return {"id": template.id, "status": template.status}


@router.patch("/task-templates/{template_id}")
def update_template(template_id: int, payload: TaskTemplateUpdate, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    template = db.get(TaskTemplate, template_id)
    if template is None:
        raise HTTPException(404, "template not found")
    if template.status is not PublicationStatus.DRAFT:
        raise HTTPException(409, "only draft templates can be edited")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None or field in {"time_range", "due_time", "acceptance_criteria"}:
            setattr(template, field, value)
    db.add(AuditLog(actor_id=current.id, action="task_template.update", resource_type="task_template", resource_id=str(template.id)))
    db.commit()
    return {"id": template.id, "status": template.status, **{field: getattr(template, field) for field in updates}}


@router.post("/task-templates/{template_id}/publish")
def publish_template(template_id: int, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    template = db.get(TaskTemplate, template_id)
    if not template:
        raise HTTPException(404, "template not found")
    if not template.position_code or not template.frequency or not template.content.strip() or not template.due_time:
        raise HTTPException(422, "position, frequency, content and due time are required")
    if template.frequency is Frequency.WEEKLY and template.schedule_rule.get("weekday") not in range(5):
        raise HTTPException(422, "weekly template requires weekday 0-4")
    if template.frequency in {Frequency.MONTHLY, Frequency.SEMESTER}:
        dates = template.schedule_rule.get("dates")
        if not dates or not all(isinstance(value, str) for value in dates):
            raise HTTPException(422, "monthly/semester template requires explicit ISO dates")
    if template.frequency is Frequency.SECURITY_WEEKEND and template.position_code is not PositionCode.SECURITY:
        raise HTTPException(422, "security weekend frequency only applies to security position")
    template.status = PublicationStatus.PUBLISHED
    db.add(AuditLog(actor_id=current.id, action="task_template.publish", resource_type="task_template", resource_id=str(template.id)))
    db.commit()
    return {"id": template.id, "status": template.status}


@router.put("/calendar/{target_date}")
def set_calendar(target_date: date, payload: CalendarUpdate, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(WorkCalendar, target_date)
    if row is None:
        row = WorkCalendar(date=target_date, kind=payload.kind, reason=payload.reason)
        db.add(row)
    else:
        row.kind, row.reason = payload.kind, payload.reason
    db.add(AuditLog(actor_id=current.id, action="calendar.set", resource_type="work_calendar", resource_id=target_date.isoformat()))
    db.commit()
    return {"date": row.date, "kind": row.kind, "reason": row.reason}


@router.post("/tasks/generate")
def generate_tasks(target_date: date, _: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    result = generate_tasks_for_date(db, target_date)
    return {"created": result.created, "skipped": result.skipped, "anomalies": result.anomalies}


@router.get("/knowledge-documents/{document_id}/drafts")
def list_import_drafts(document_id: int, _: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(KnowledgeDocument, document_id) is None:
        raise HTTPException(404, "document not found")
    chunks = db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id).order_by(KnowledgeChunk.source_sheet, KnowledgeChunk.source_row)).all()
    templates = db.scalars(select(TaskTemplate).where(TaskTemplate.source_document_id == document_id).order_by(TaskTemplate.id)).all()
    return {"chunks": [{"id": c.id, "position_code": c.position_code, "frequency": c.frequency, "task_label": c.task_label, "content": c.content, "sheet": c.source_sheet, "row": c.source_row, "status": c.publish_status} for c in chunks], "templates": [{"id": t.id, "position_code": t.position_code, "frequency": t.frequency, "title": t.title, "content": t.content, "sheet": t.source_sheet, "row": t.source_row, "status": t.status} for t in templates]}


@router.post("/knowledge-chunks/{chunk_id}/publish")
def publish_chunk(chunk_id: int, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    chunk = db.get(KnowledgeChunk, chunk_id)
    if not chunk or not chunk.position_code or not chunk.content.strip():
        raise HTTPException(422, "knowledge chunk requires position and content")
    chunk.publish_status = PublicationStatus.PUBLISHED
    db.add(AuditLog(actor_id=current.id, action="knowledge.publish", resource_type="knowledge_chunk", resource_id=str(chunk.id)))
    db.commit()
    return {"id": chunk.id, "status": chunk.publish_status}


@router.patch("/knowledge-chunks/{chunk_id}")
def update_knowledge_chunk(chunk_id: int, payload: KnowledgeChunkUpdate, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    chunk = db.get(KnowledgeChunk, chunk_id)
    if chunk is None:
        raise HTTPException(404, "knowledge chunk not found")
    if chunk.publish_status is not PublicationStatus.DRAFT:
        raise HTTPException(409, "only draft knowledge can be edited")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(chunk, field, value)
    db.add(AuditLog(actor_id=current.id, action="knowledge.update", resource_type="knowledge_chunk", resource_id=str(chunk.id)))
    db.commit()
    return {"id": chunk.id, "position_code": chunk.position_code, "frequency": chunk.frequency, "task_label": chunk.task_label, "status": chunk.publish_status}


@router.post("/change-requests/{request_id}/approve")
def approve_change(request_id: int, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    item = review_change_request(db, request_id, current, True)
    return {"id": item.id, "status": item.status}


@router.post("/change-requests/{request_id}/reject")
def reject_change(request_id: int, payload: ChangeReview, current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    item = review_change_request(db, request_id, current, False, payload.reason)
    return {"id": item.id, "status": item.status, "reason": item.review_note}


@router.post("/knowledge-documents/import-excel", status_code=201)
async def upload_knowledge(file: UploadFile = File(...), current: Staff = Depends(require_admin), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(415, "only .xlsx workbooks are supported")
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "file exceeds 10 MB")
    try:
        document, row_count = import_workbook(db, current, file.filename, content)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {"id": document.id, "file_name": document.file_name, "file_hash": document.file_hash, "parse_status": document.parse_status, "draft_rows": row_count}
