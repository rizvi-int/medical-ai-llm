from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"

    # Database Configuration
    database_url: str
    sync_database_url: str

    # Qdrant Configuration
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "medical_documents"

    # Application Configuration
    app_name: str = "Medical Notes Processor"
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"

    # CORS Configuration
    allowed_origins: List[str] | str = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # External APIs
    nlm_api_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    clinicaltables_api_base_url: str = "https://clinicaltables.nlm.nih.gov/api"


settings = Settings()