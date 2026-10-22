from datetime import date, datetime

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    note: str = ""
    photo_keys: list[str] = Field(default_factory=list, max_length=3)


class ChangeRequestCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ChangeReview(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
