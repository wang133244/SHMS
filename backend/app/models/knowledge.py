from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.models.enums import PositionCode, ReviewStatus, PublicationStatus


@compiles(Vector, "sqlite")
def compile_vector_for_sqlite(type_, compiler, **kwargs):
    return "JSON"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(240), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    position_code: Mapped[PositionCode | None] = mapped_column(Enum(PositionCode), nullable=True, index=True)
    frequency: Mapped[str | None] = mapped_column(String(40))
    task_label: Mapped[str | None] = mapped_column(String(160))
    source_sheet: Mapped[str] = mapped_column(String(120), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    publish_status: Mapped[PublicationStatus] = mapped_column(Enum(PublicationStatus), default=PublicationStatus.DRAFT, nullable=False)
