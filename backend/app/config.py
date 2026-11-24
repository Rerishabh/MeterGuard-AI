"""
MeterGuard AI: Application Configuration Module
Uses Pydantic Settings to load configuration from environment variables and .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# PROJECT_ROOT: Points to root repository directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings with environment variable fallbacks."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database: strictly required via environment variable or .env file.
    DATABASE_URL: str

    # API Server & Port Binding (Render injects PORT, local fallback API_PORT)
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 5000
    PORT: int | None = None

    # Configurable CORS Origins (comma-separated origins, e.g. 'https://meterguard-ai.pages.dev')
    CORS_ORIGINS: str = ""

    # ML Artifacts (relative to PROJECT_ROOT or absolute)
    MODEL1_PATH: str = "models/isolation_forest_final.joblib"
    MODEL2_PATH: str = "models/sih_fault_detection_model_2.joblib"
    ML_ARTIFACTS_DIR: str = "ml/artifacts"

    # Phase 3B: Gemini GenAI Configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    @property
    def effective_port(self) -> int:
        return self.PORT if self.PORT is not None else self.API_PORT

    def get_model1_path(self) -> Path:
        p = Path(self.MODEL1_PATH)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    def get_model2_path(self) -> Path:
        p = Path(self.MODEL2_PATH)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    def get_artifacts_dir(self) -> Path:
        p = Path(self.ML_ARTIFACTS_DIR)
        return p if p.is_absolute() else (PROJECT_ROOT / p)


settings = Settings()
