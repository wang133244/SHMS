from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import CalendarKind, Frequency, PositionCode, Role


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    employee_no: str = Field(min_length=1, max_length=40)
    phone: str = Field(pattern=r"^1\d{10}$")
    password: str = Field(min_length=8, max_length=128)
    position_code: PositionCode | None = None
    role: Role = Role.EMPLOYEE


class StaffPositionUpdate(BaseModel):
    position_code: PositionCode


class TaskTemplateCreate(BaseModel):
    position_code: PositionCode
    title: str = Field(min_length=1, max_length=160)
    frequency: Frequency
    schedule_rule: dict = Field(default_factory=dict)
    time_range: str | None = None
    due_time: str | None = None
    content: str = Field(min_length=1)
    acceptance_criteria: str | None = None


class TaskTemplateUpdate(BaseModel):
    position_code: PositionCode | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    frequency: Frequency | None = None
    schedule_rule: dict | None = None
    time_range: str | None = None
    due_time: str | None = None
    content: str | None = Field(default=None, min_length=1)
    acceptance_criteria: str | None = None


class KnowledgeChunkUpdate(BaseModel):
    position_code: PositionCode | None = None
    frequency: str | None = Field(default=None, max_length=40)
    task_label: str | None = Field(default=None, max_length=160)


class CalendarUpdate(BaseModel):
    kind: CalendarKind
    reason: str | None = None


class PositionCalendarRead(BaseModel):
    date: date
    kind: CalendarKind
    reason: str | None
