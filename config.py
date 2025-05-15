from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    database_url: str = "sqlite:///./bookmarks.db"
    request_limit: int = 10  # 每分钟请求限制

    class Config:
        env_file = ".env"


settings = Settings()