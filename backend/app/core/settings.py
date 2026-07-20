from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    open_router_key: str
    database_url: str = "sqlite+aiosqlite:///./myquant.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # let FE-only vars like SESSION_SECRET live in a shared .env without erroring here
    )


settings = Settings()  # type: ignore
