import redis.asyncio as redis
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from starlette.middleware.cors import CORSMiddleware

from routers import bookmarks, classify

app = FastAPI()

# 配置中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化限流器
@app.on_event("startup")
async def startup():
    redis_client = redis.from_url("redis://localhost:6379")
    await FastAPILimiter.init(redis_client)

# 包含路由
app.include_router(
    bookmarks.router,
    prefix="/bookmarks",
    tags=["Bookmarks"]
)

app.include_router(
    classify.router,
    prefix="/classify",
    tags=["Classification"]
)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}