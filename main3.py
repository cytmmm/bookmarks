import json

import openai
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import requests

from starlette.middleware.cors import CORSMiddleware

from Bookmark import SessionLocal, Bookmark

# 初始化 FastAPI 应用
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源访问
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)


# Pydantic模型：用于请求体和响应体
class BookmarkCreate(BaseModel):
    title: str
    url: str
    tags: Optional[str] = None
    expiration_date: Optional[datetime] = None


class BookmarkResponse(BaseModel):
    id: int
    title: str
    url: str
    tags: Optional[str]
    frequency: int
    last_visited: datetime
    expiration_date: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True


# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 添加书签
@app.post("/bookmarks/", response_model=BookmarkResponse)
def add_bookmark(bookmark: BookmarkCreate, db: Session = Depends(get_db)):
    db_bookmark = Bookmark(title=bookmark.title, url=bookmark.url, tags=bookmark.tags,
                           expiration_date=bookmark.expiration_date)
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark


# 获取所有书签
@app.get("/bookmarks/", response_model=List[BookmarkResponse])
def get_bookmarks(db: Session = Depends(get_db)):
    bookmarks = db.query(Bookmark).all()
    return bookmarks


# 更新书签
@app.put("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
def update_bookmark(bookmark_id: int, bookmark: BookmarkCreate, db: Session = Depends(get_db)):
    db_bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not db_bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db_bookmark.title = bookmark.title
    db_bookmark.url = bookmark.url
    db_bookmark.tags = bookmark.tags
    db_bookmark.expiration_date = bookmark.expiration_date
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark


# 删除书签
@app.delete("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    db_bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not db_bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(db_bookmark)
    db.commit()
    return db_bookmark


# 过期提醒
@app.get("/bookmarks/expire", response_model=List[BookmarkResponse])
def check_expiration(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    expired_bookmarks = db.query(Bookmark).filter(Bookmark.expiration_date <= now).all()
    return expired_bookmarks


# 新增 classify_bookmarks 接口
@app.post("/classify_bookmarks/", response_model=List[BookmarkResponse])
def classify_bookmarks(bookmarks: List[BookmarkCreate], db: Session = Depends(get_db)):
    """
    使用 DeepSeek 进行书签分类，并根据分类结果更新书签标签，若书签不存在则新增。
    """
    # 书签数据转换成 DeepSeek 需要的格式
    bookmark_data = [{"title": bookmark.title, "url": bookmark.url} for bookmark in bookmarks]

    # 调用 DeepSeek API 进行分类
    classified_bookmarks = classify_with_deepseek(bookmark_data)

    # 更新数据库中的书签 tags 或新增书签
    for classified_bookmark in classified_bookmarks:
        # 查找对应的数据库书签
        db_bookmark = db.query(Bookmark).filter(Bookmark.title == classified_bookmark['title']).first()

        # 如果书签已经存在，更新 tags
        if db_bookmark:
            # 现有 tags
            existing_tags = db_bookmark.tags if db_bookmark.tags else ""
            new_tags = classified_bookmark['tags']

            # 如果现有的 tags 不为空，并且分类结果的 tags 不一样，则进行合并
            if existing_tags:
                # 合并标签，避免重复
                tags_set = set(existing_tags.split(", ")) | set(new_tags.split(", "))
                db_bookmark.tags = ", ".join(tags_set)
            else:
                # 如果没有现有 tags，则直接设置新标签
                db_bookmark.tags = new_tags
            db.commit()

        else:
            # 如果书签不存在，新增书签
            db_bookmark = Bookmark(
                title=classified_bookmark['title'],
                url=classified_bookmark['url'],
                tags=classified_bookmark['tags']
            )
            db.add(db_bookmark)
            db.commit()

    # 返回更新后的书签列表
    return db.query(Bookmark).filter(Bookmark.title.in_([bookmark.title for bookmark in bookmarks])).all()


def classify_with_deepseek(bookmarks):
    """
    使用 DeepSeek API 对书签进行分类。
    """
    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-8e4a160524074993ac21b0b6f9c39184",  # 请替换为你的 DeepSeek API 密钥
    }

    # 将书签信息格式化成字符串
    bookmarks_text = "\n".join([f"Title: {bookmark['title']}, URL: {bookmark['url']}" for bookmark in bookmarks])

    print(bookmarks_text)
    # 请求的payload
    payload = {
        "models.py": "deepseek-chat",
        "messages": [
            {"role": "user", "content": f"Classify the following bookmarks: \n{bookmarks_text} 返回的结果是json格式 里面包含title url tags，tags返回最相关的一个tags 相似的内容归类到一个tags里"}
        ],
        "stream": False
    }

    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # 处理响应
        if response.status_code == 200:
            classified_data = response.json()
            print(classified_data['choices'][0]['message']['content'])
            # 获取分类的文本内容
            classification_text = classified_data['choices'][0]['message']['content']
            return parse_classification_results(classification_text)
        else:
            raise Exception(f"Error in DeepSeek API: {response.status_code}, {response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error in DeepSeek API request: {str(e)}")


def parse_classification_results(classification_text):
    """
    解析 DeepSeek 返回的分类文本，将其转化为书签对象列表。
    """
    try:
        # 从文本中提取有效的 JSON 数据
        json_start = classification_text.find('[')  # JSON 数据开始的位置
        json_end = classification_text.rfind(']')  # JSON 数据结束的位置
        json_str = classification_text[json_start:json_end + 1]

        # 将提取的 JSON 字符串转换为 Python 对象
        classified_data = json.loads(json_str)

        # 初始化分类后的书签数据
        categorized_bookmarks = []

        # 遍历 JSON 数据，组织每个书签的分类
        for item in classified_data:
            categorized_bookmarks.append({
                'title': item.get('title', '').strip(),
                'url': item.get('url', '').strip(),
                'tags': item.get('tags', '').strip()
            })

        # 返回分类后的书签列表
        return categorized_bookmarks

    except Exception as e:
        raise Exception(f"Error parsing classification results: {str(e)}")