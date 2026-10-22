from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PublicationStatus, PositionCode
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument


def retrieve_published_chunks(db: Session, position_code: PositionCode, query: str, limit: int = 5) -> list[KnowledgeChunk]:
    statement = select(KnowledgeChunk).where(
        KnowledgeChunk.position_code == position_code,
        KnowledgeChunk.publish_status == PublicationStatus.PUBLISHED,
    )
    if db.bind and db.bind.dialect.name == "postgresql":
        from app.services.embeddings import embed_text

        vector = embed_text(query)
        if vector is None:
            return []
        statement = statement.order_by(KnowledgeChunk.embedding.cosine_distance(vector)).limit(limit)
        return list(db.scalars(statement))

    terms = [term for term in query.strip().split() if len(term) > 1]
    chunks = list(db.scalars(statement.order_by(KnowledgeChunk.id.desc()).limit(100)))
    if not terms:
        return chunks[:limit]
    ranked = sorted(chunks, key=lambda chunk: sum(term.lower() in chunk.content.lower() for term in terms), reverse=True)
    return [chunk for chunk in ranked if any(term.lower() in chunk.content.lower() for term in terms)][:limit]


def source_for_chunk(db: Session, chunk: KnowledgeChunk) -> dict:
    document = db.get(KnowledgeDocument, chunk.document_id)
    return {
        "chunk_id": chunk.id,
        "file_name": document.file_name if document else "",
        "document_version": document.version if document else None,
        "sheet": chunk.source_sheet,
        "row": chunk.source_row,
    }
