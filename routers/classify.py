from fastapi import APIRouter, Depends, HTTPException
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session
from database import get_db
from utils.ai_classifier import DeepSeekClassifier
import schemas, crud
from typing import List

router = APIRouter()


@router.post(
    "/",
    response_model=List[schemas.BookmarkResponse],
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
def classify_bookmarks(
        bookmarks: List[schemas.BookmarkCreate],
        db: Session = Depends(get_db)
):
    """使用AI分类书签"""
    classifier = DeepSeekClassifier()

    try:
        # 转换Pydantic模型到字典
        bookmarks_data = [b.dict() for b in bookmarks]

        # 获取分类结果
        classified = classifier.classify(bookmarks_data)

        # 处理数据库操作
        results = []
        # 创建一个存储所有书签更新或创建的操作，减少数据库的频繁访问
        for item in classified:
            db_bookmark = crud.get_bookmark_by_url(db, url=item["url"])

            if db_bookmark:
                # 合并标签
                merged_tags = merge_tags(db_bookmark.tags, item["tags"])
                db_bookmark = crud.update_bookmark_tags(
                    db,
                    bookmark_id=db_bookmark.id,
                    tags=merged_tags
                )
            else:
                # 创建新书签
                db_bookmark = crud.create_bookmark(db, schemas.BookmarkCreate(**item))

            results.append(db_bookmark)

        return results

    except HTTPException as he:
        # 重新抛出HTTP异常
        raise he
    except Exception as e:
        # 捕获其他异常并返回500错误
        print(f"Error during bookmark classification: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def merge_tags(existing_tags: str, new_tags: str) -> str:
    """合并现有标签和新标签"""
    existing_tags_set = set(existing_tags.split(", ")) if existing_tags else set()
    new_tags_set = set(new_tags.split(", ")) if new_tags else set()
    return ", ".join(existing_tags_set | new_tags_set)  # 使用集合合并，去重并合并