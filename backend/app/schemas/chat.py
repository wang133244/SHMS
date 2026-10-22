from pydantic import BaseModel, Field


class ChatAsk(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class Citation(BaseModel):
    chunk_id: int
    file_name: str
    document_version: int | None
    sheet: str
    row: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    refusal: bool
