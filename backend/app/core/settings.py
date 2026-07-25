from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    open_router_key: str
    telegram_page_password: str = "changeme"
    telegram_bot_token: str = ""
    telegram_allowed_chat_id: str = ""
    telegram_user_id: str = ""
    database_url: str = "sqlite+aiosqlite:///./myquant.db"

    redis_url: str = "redis://localhost:6379/0"
    chroma_path: str = "./data/chroma"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore
