from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "EEG Backend"
    eeg_library_path: str = "./eeg"
    postgres_dsn: str = Field(default="postgresql+psycopg://eeg:eeg@localhost:5432/eeg")
    redis_dsn: str = Field(default="redis://localhost:6379/0")

    class Config:
        env_file = ".env"


settings = Settings()
