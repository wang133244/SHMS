from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tasks import CalendarDay, TemplateSchedule, can_generate_for_date
from app.models.audit import AuditLog
from app.models.enums import CalendarKind, EmploymentStatus, PositionCode, PublicationStatus, Role
from app.models.staff import Position, Staff, WorkCalendar
from app.models.task import TaskInstance, TaskTemplate


@dataclass(frozen=True)
class GenerationResult:
    created: int
    skipped: int
    anomalies: tuple[str, ...]


def _calendar_day(target: date, override: WorkCalendar | None) -> CalendarDay:
    if override:
        return CalendarDay(override.kind, target.weekday())
    kind = CalendarKind.WORKDAY if target.weekday() < 5 else CalendarKind.WEEKEND
    return CalendarDay(kind, target.weekday())


def _dates_for_template(template: TaskTemplate) -> frozenset[date]:
    raw_dates = template.schedule_rule.get("dates", [])
    try:
        return frozenset(date.fromisoformat(value) for value in raw_dates)
    except (TypeError, ValueError):
        return frozenset()


def generate_tasks_for_date(db: Session, target: date) -> GenerationResult:
    day = _calendar_day(target, db.get(WorkCalendar, target))
    templates = db.scalars(select(TaskTemplate).where(TaskTemplate.status == PublicationStatus.PUBLISHED)).all()
    created = skipped = 0
    anomalies = []
    for template in templates:
        if not template.position_code or not template.frequency or not template.content.strip() or not template.due_time:
            anomalies.append(f"template:{template.id}:incomplete")
            continue
        matching_dates = _dates_for_template(template)
        schedule = TemplateSchedule(
            position=template.position_code,
            frequency=template.frequency,
            weekday=template.schedule_rule.get("weekday"),
            matching_dates=matching_dates,
        )
        if not can_generate_for_date(schedule, target, day):
            skipped += 1
            continue
        staff = db.scalars(select(Staff).join(Position).where(Position.code == template.position_code, Staff.employment_status == EmploymentStatus.ACTIVE, Staff.role == Role.EMPLOYEE)).all()
        if len(staff) != 1:
            anomalies.append(f"template:{template.id}:active_staff_count:{len(staff)}")
            continue
        existing = db.scalar(select(TaskInstance.id).where(
            TaskInstance.template_id == template.id,
            TaskInstance.staff_id == staff[0].id,
            TaskInstance.due_date == target,
        ))
        if existing:
            skipped += 1
            continue
        try:
            due_time = time.fromisoformat(template.due_time)
        except ValueError:
            anomalies.append(f"template:{template.id}:invalid_due_time")
            continue
        db.add(TaskInstance(
            template_id=template.id,
            template_version=template.version,
            staff_id=staff[0].id,
            position_code_snapshot=template.position_code,
            due_date=target,
            due_at=datetime.combine(target, due_time),
            generation_reason=f"template:{template.id}:v{template.version}",
        ))
        created += 1
    for anomaly in anomalies:
        db.add(AuditLog(action="task.generation_anomaly", resource_type="task_template", resource_id=anomaly.split(":")[1], details={"reason": anomaly, "date": target.isoformat()}))
    db.commit()
    return GenerationResult(created, skipped, tuple(anomalies))
