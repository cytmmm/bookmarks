from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

import crud
import schemas
from database import get_db
from routers.classify import merge_tags
from utils.ai_classifier import DeepSeekClassifier

router = APIRouter()


# 创建新书签
@router.post("/", response_model=schemas.BookmarkResponse)
async def create_bookmark(
        bookmark: schemas.BookmarkCreate,
        db: Session = Depends(get_db)
):
    """创建新书签"""
    # 检查URL是否已存在
    existing = crud.get_bookmark_by_url(db, url=str(bookmark.url))
    if existing:
        raise HTTPException(status_code=400, detail="URL already exists")

    return crud.create_bookmark(db, bookmark=bookmark)


# 获取所有书签
@router.get("/", response_model=List[schemas.BookmarkResponse])
def get_bookmarks(db: Session = Depends(get_db)):
    """获取所有书签"""
    bookmarks = crud.get_bookmarks(db)
    return bookmarks


# 更新书签
@router.put("/{bookmark_id}", response_model=schemas.BookmarkResponse)
def update_bookmark(
        bookmark_id: int,
        bookmark: schemas.BookmarkCreate,
        db: Session = Depends(get_db)
):
    """更新书签"""
    db_bookmark = crud.get_bookmark(db, bookmark_id=bookmark_id)
    if not db_bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    # 更新书签
    return crud.update_bookmark(db, bookmark_id=bookmark_id, bookmark=bookmark)


# 删除书签
@router.delete("/{bookmark_id}", response_model=schemas.BookmarkResponse)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    """删除书签"""
    db_bookmark = crud.get_bookmark(db, bookmark_id=bookmark_id)
    if not db_bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    # 删除书签
    return crud.delete_bookmark(db, bookmark_id=bookmark_id)


# 过期提醒
@router.get("/expire", response_model=List[schemas.BookmarkResponse])
def check_expiration(db: Session = Depends(get_db)):
    """检查书签是否过期"""
    now = datetime.utcnow()
    expired_bookmarks = crud.get_bookmarks(db, expiration_date__lte=now)
    return expired_bookmarks