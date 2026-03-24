from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EEG Backend"
    eeg_data_dir: str = Field(default="./eeg", alias="EEG_DATA_DIR")
    postgres_dsn: str = Field(default="postgresql+psycopg://eeg:eeg@localhost:5432/eeg", alias="POSTGRES_DSN")
    redis_dsn: str = Field(default="redis://localhost:6379/0", alias="REDIS_DSN")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)


settings = Settings()
