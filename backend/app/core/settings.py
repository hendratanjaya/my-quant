from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    open_router_key: str
    database_url: str = "sqlite+aiosqlite:///./myquant.db"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


settings = Settings()  # type: ignore
