from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DOC_PATH: str = "data"
    CHROMA_DB_DIR: str = "./chroma_database"
    COLLECTION_NAME: str = "thai_labor_law"
    DEFAULT_COLLECTION_ID: str = "default"
    VECTOR_PIPELINE_VERSION: str = "phase1-incremental-v1"

    EMBED_MODEL_NAME: str = "airesearch/WangchanX-Legal-ThaiCCL-Retriever"
    ENABLE_RERANKER: bool = False
    RERANK_MODEL_NAME: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    LLM_MODEL_NAME: str = "gpt-5.4-mini"
    SUPPORTED_LLM_MODELS: list[str] = Field(
        default_factory=lambda: ["gpt-5.4", "gpt-5.4-mini", "gpt-4o"]
    )
    OPENAI_API_KEY: str = ""

    TOP_K_RESULTS: int = 3
    DEFAULT_SEARCH_STRATEGY: str = "hybrid"
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
    AUTO_INIT_COLLECTION: bool = True

    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

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
