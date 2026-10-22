from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import Frequency, PositionCode, PublicationStatus, ReviewStatus
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.staff import Staff
from app.models.task import TaskTemplate
from app.services.excel_import import parse_workbook


def import_workbook(db: Session, admin: Staff, filename: str, content: bytes) -> tuple[KnowledgeDocument, int]:
    parsed = parse_workbook(content, filename)
    settings = get_settings()
    path = Path(settings.upload_dir) / "documents"
    path.mkdir(parents=True, exist_ok=True)
    storage_key = f"documents/{parsed.file_hash}.xlsx"
    (Path(settings.upload_dir) / storage_key).write_bytes(content)
    document = KnowledgeDocument(file_name=Path(filename).name, file_hash=parsed.file_hash, uploaded_by=admin.id, review_status=ReviewStatus.PENDING, parse_status="parsed", storage_key=storage_key)
    db.add(document)
    db.flush()
    frequency_map = {frequency.value: frequency for frequency in Frequency}
    for row in parsed.rows:
        position = PositionCode(row.position_code) if row.position_code else None
        chunk = KnowledgeChunk(document_id=document.id, position_code=position, frequency=row.frequency, task_label=row.task_label, source_sheet=row.source_sheet, source_row=row.source_row, content=row.content, publish_status=PublicationStatus.DRAFT)
        db.add(chunk)
        frequency = frequency_map.get(row.frequency)
        if row.task_label and row.content:
            db.add(TaskTemplate(position_code=position, title=row.task_label[:160], frequency=frequency, schedule_rule={}, time_range=row.time_range, content=row.content, status=PublicationStatus.DRAFT, source_document_id=document.id, source_sheet=row.source_sheet, source_row=row.source_row))
    db.commit()
    db.refresh(document)
    return document, len(parsed.rows)
