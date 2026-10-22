from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Frequency, PositionCode, PublicationStatus, ReviewStatus, TaskStatus


class TaskTemplate(Base):
    __tablename__ = "task_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    position_code: Mapped[PositionCode | None] = mapped_column(Enum(PositionCode), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    frequency: Mapped[Frequency | None] = mapped_column(Enum(Frequency), nullable=True)
    schedule_rule: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    time_range: Mapped[str | None] = mapped_column(String(80))
    due_time: Mapped[str | None] = mapped_column(String(8))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PublicationStatus] = mapped_column(Enum(PublicationStatus), default=PublicationStatus.DRAFT)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_documents.id"))
    source_sheet: Mapped[str | None] = mapped_column(String(120))
    source_row: Mapped[int | None] = mapped_column(Integer)
    requires_workday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TaskInstance(Base):
    __tablename__ = "task_instances"
    __table_args__ = (UniqueConstraint("template_id", "staff_id", "due_date", name="uq_task_template_staff_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("task_templates.id"), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False, index=True)
    position_code_snapshot: Mapped[PositionCode] = mapped_column(Enum(PositionCode), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    generation_reason: Mapped[str] = mapped_column(String(120), nullable=False)
    template: Mapped[TaskTemplate] = relationship()
    submissions: Mapped[list["TaskSubmission"]] = relationship(order_by="TaskSubmission.version")


class TaskSubmission(Base):
    __tablename__ = "task_submissions"
    __table_args__ = (UniqueConstraint("task_instance_id", "version", name="uq_submission_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_instance_id: Mapped[int] = mapped_column(ForeignKey("task_instances.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    photo_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_instance_id: Mapped[int] = mapped_column(ForeignKey("task_instances.id"), nullable=False, index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
