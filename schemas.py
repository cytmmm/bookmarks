from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List


class BookmarkBase(BaseModel):
    title: str
    url: str
    tags: Optional[str] = None
    expiration_date: Optional[datetime] = None


class BookmarkCreate(BookmarkBase):
    title: str
    url: str
    tags: Optional[str] = None
    expiration_date: Optional[datetime] = None


class BookmarkResponse(BookmarkBase):
    id: int
    class Config:
        orm_mode = True


class ClassificationRequest(BaseModel):
    bookmarks: List[BookmarkCreate]
