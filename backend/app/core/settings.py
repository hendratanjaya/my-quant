from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    open_router_key: str
    telegram_page_password: str
    telegram_bot_token: str
    telegram_allowed_chat_id: str
    database_url: str

    redis_url: str
    chroma_path: str
    allowed_origins: list[str]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore
