from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Paths
    DOC_PATH: str = "data/"
    CHROMA_DB_DIR: str = "./chroma_database"
    COLLECTION_NAME: str = "thai_labor_law"

    # Models
    EMBED_MODEL_NAME: str = "airesearch/WangchanX-Legal-ThaiCCL-Retriever"
    LLM_MODEL_NAME: str = "gpt-5.4-mini"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Retrieval
    TOP_K_RESULTS: int = 3
    AUTO_INIT_COLLECTION: bool = True

    # FastAPI
    API_V1_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_doc_path(self) -> Path:
        configured_path = Path(self.DOC_PATH)
        fallback_path = Path("data")

        if configured_path.exists():
            return configured_path
        if fallback_path.exists():
            return fallback_path
        return configured_path


settings = Settings()

