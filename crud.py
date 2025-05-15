from sqlalchemy.orm import Session
import models, schemas


def get_bookmark(db: Session, bookmark_id: int):
    """根据ID获取书签"""
    return db.query(models.Bookmark).filter(models.Bookmark.id == bookmark_id).first()


def get_bookmarks(db: Session, skip: int = 0, limit: int = 100):
    """获取书签列表，支持分页"""
    return db.query(models.Bookmark).offset(skip).limit(limit).all()


def delete_bookmark(db: Session, bookmark_id: int):
    db_bookmark = db.query(models.Bookmark).filter(models.Bookmark.id == bookmark_id).first()
    if not db_bookmark:
        return None
    db.delete(db_bookmark)
    db.commit()
    return db_bookmark


def create_bookmark(db: Session, bookmark: schemas.BookmarkCreate):
    """创建书签"""
    db_bookmark = models.Bookmark(**bookmark.dict())
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark


def get_bookmark_by_url(db: Session, url: str):
    """根据URL查找书签"""
    return db.query(models.Bookmark).filter(models.Bookmark.url == url).first()


def update_bookmark_tags(db: Session, bookmark_id: int, tags: str):
    """更新书签的标签"""
    db_bookmark = db.query(models.Bookmark).filter(models.Bookmark.id == bookmark_id).first()
    if db_bookmark:
        db_bookmark.tags = tags
        db.commit()
        db.refresh(db_bookmark)
        return db_bookmark
    return None
