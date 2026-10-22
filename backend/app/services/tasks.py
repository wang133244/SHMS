from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tasks import next_submission_version, transition_task
from app.models.audit import AuditLog
from app.models.enums import ReviewStatus, Role, TaskStatus
from app.models.staff import Staff
from app.models.task import ChangeRequest, TaskInstance, TaskSubmission


def list_my_tasks(db: Session, staff_id: int, target_date: date | None = None) -> list[TaskInstance]:
    statement = select(TaskInstance).where(TaskInstance.staff_id == staff_id)
    if target_date:
        statement = statement.where(TaskInstance.due_date == target_date)
    return list(db.scalars(statement.order_by(TaskInstance.due_date, TaskInstance.id)))


def _task_for_staff(db: Session, task_id: int, staff: Staff) -> TaskInstance:
    query = select(TaskInstance).where(TaskInstance.id == task_id)
    if staff.role is not Role.ADMIN:
        query = query.where(TaskInstance.staff_id == staff.id)
    task = db.scalar(query)
    if not task:
        raise HTTPException(404, "task not found")
    return task


def get_task_detail(db: Session, task_id: int, staff: Staff) -> dict:
    task = _task_for_staff(db, task_id, staff)
    return {
        "id": task.id,
        "staff_id": task.staff_id,
        "title": task.template.title,
        "content": task.template.content,
        "acceptance_criteria": task.template.acceptance_criteria,
        "time_range": task.template.time_range,
        "status": task.status,
        "due_date": task.due_date,
        "due_at": task.due_at,
        "submissions": [
            {"id": item.id, "version": item.version, "submitted_at": item.submitted_at, "note": item.note, "photo_keys": item.photo_keys}
            for item in task.submissions
        ],
    }


def submit_task(db: Session, task_id: int, staff: Staff, note: str, photo_keys: list[str]) -> TaskSubmission:
    task = _task_for_staff(db, task_id, staff)
    if task.status is not TaskStatus.PENDING:
        raise HTTPException(409, "task is not pending")
    if len(photo_keys) > 3:
        raise HTTPException(422, "at most 3 photos are allowed")
    submission = TaskSubmission(task_instance_id=task.id, version=next_submission_version([item.version for item in task.submissions]), submitted_at=datetime.now(timezone.utc), note=note, photo_keys=photo_keys)
    task.status = transition_task(task.status, "submit")
    db.add_all([submission, AuditLog(actor_id=staff.id, action="task.submit", resource_type="task", resource_id=str(task.id))])
    db.commit(); db.refresh(submission)
    return submission


def request_task_change(db: Session, task_id: int, staff: Staff, reason: str) -> ChangeRequest:
    task = _task_for_staff(db, task_id, staff)
    if task.status is not TaskStatus.SUBMITTED:
        raise HTTPException(409, "task is not submitted")
    task.status = transition_task(task.status, "request_change")
    request = ChangeRequest(task_instance_id=task.id, requester_id=staff.id, reason=reason.strip())
    db.add_all([request, AuditLog(actor_id=staff.id, action="task.change_request", resource_type="task", resource_id=str(task.id))])
    db.commit(); db.refresh(request)
    return request


def review_change_request(db: Session, request_id: int, admin: Staff, approved: bool, reason: str | None = None) -> ChangeRequest:
    request = db.get(ChangeRequest, request_id)
    if not request or request.status is not ReviewStatus.PENDING:
        raise HTTPException(409, "change request is not pending")
    if not approved and not (reason or "").strip():
        raise HTTPException(422, "reason is required when rejecting")
    task = db.get(TaskInstance, request.task_instance_id)
    if not task or task.status is not TaskStatus.CHANGE_PENDING:
        raise HTTPException(409, "task is not awaiting review")
    task.status = transition_task(task.status, "approve" if approved else "reject", reason)
    request.status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
    request.reviewer_id, request.review_note, request.reviewed_at = admin.id, (reason or "").strip() or None, datetime.now(timezone.utc)
    db.add(AuditLog(actor_id=admin.id, action="task.change_approved" if approved else "task.change_rejected", resource_type="change_request", resource_id=str(request.id)))
    db.commit(); db.refresh(request)
    return request
