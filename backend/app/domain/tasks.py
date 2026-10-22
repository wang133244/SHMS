from dataclasses import dataclass, field
from datetime import date
from app.models.enums import CalendarKind, Frequency, PositionCode, TaskStatus


@dataclass(frozen=True)
class CalendarDay:
    kind: CalendarKind
    weekday: int | None = None


@dataclass(frozen=True)
class TemplateSchedule:
    position: PositionCode
    frequency: Frequency
    weekday: int | None = None
    matching_dates: frozenset[date] = field(default_factory=frozenset)


def is_regular_workday(day: CalendarDay) -> bool:
    return day.kind in {CalendarKind.WORKDAY, CalendarKind.MAKEUP_WORKDAY}


def can_generate_for_date(schedule: TemplateSchedule, target: date, calendar: CalendarDay) -> bool:
    if schedule.position is PositionCode.SECURITY:
        if schedule.frequency is Frequency.SECURITY_WEEKEND:
            return calendar.kind is CalendarKind.WEEKEND
        if schedule.frequency is Frequency.DAILY:
            return calendar.kind in {
                CalendarKind.WORKDAY,
                CalendarKind.MAKEUP_WORKDAY,
                CalendarKind.WEEKEND,
                CalendarKind.HOLIDAY,
                CalendarKind.SCHOOL_BREAK,
            }
        return _recurrence_matches(schedule, target, calendar, require_workday=False)

    if not is_regular_workday(calendar):
        return False
    return _recurrence_matches(schedule, target, calendar, require_workday=True)


def _recurrence_matches(schedule: TemplateSchedule, target: date, calendar: CalendarDay, require_workday: bool) -> bool:
    if require_workday and not is_regular_workday(calendar):
        return False
    if schedule.frequency is Frequency.DAILY:
        return True
    if schedule.frequency is Frequency.WEEKLY:
        weekday = schedule.weekday if schedule.weekday is not None else 0
        return target.weekday() == weekday
    if schedule.frequency in {Frequency.MONTHLY, Frequency.SEMESTER}:
        return target in schedule.matching_dates
    return False


def transition_task(status: TaskStatus, action: str, reason: str | None = None) -> TaskStatus:
    if status is TaskStatus.PENDING and action == "submit":
        return TaskStatus.SUBMITTED
    if status is TaskStatus.SUBMITTED and action == "request_change":
        return TaskStatus.CHANGE_PENDING
    if status is TaskStatus.CHANGE_PENDING and action == "approve":
        return TaskStatus.PENDING
    if status is TaskStatus.CHANGE_PENDING and action == "reject":
        if not reason or not reason.strip():
            raise ValueError("reason is required when rejecting a change request")
        return TaskStatus.SUBMITTED
    raise ValueError(f"invalid task transition: {status} -> {action}")


def next_submission_version(existing_versions: list[int]) -> int:
    return max(existing_versions, default=0) + 1
