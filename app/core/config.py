import os

import sendgrid
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    aws_access_key: str = Field(..., alias="AWS_ACCESS_KEY")
    aws_secret_access_key: str = Field(..., alias="AWS_SECRET_ACCESS_KEY")
    bucket_name: str = Field(..., alias="BUCKET_NAME")
    aws_origin: str = Field(..., alias="AWS_ORIGIN")
    mongo_url: str = Field(..., alias="MONGO_URL")
    deepgram_url: str = Field(..., alias="DEEPGRAM_URL")
    deepgram_api_key: str = Field(..., alias="DEEPGRAM_API_KEY")
    redis_url: str = Field(..., alias="REDIS_URL")
    sendgrid_api_key: str = Field(..., alias="SENDGRID_API_KEY")
    email: str = Field(..., alias="EMAIL")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../.env"),
        env_file_encoding="utf-8",
        validate_assignment=True,
        validate_default=True,
        extra="ignore",
    )


settings = Settings()
