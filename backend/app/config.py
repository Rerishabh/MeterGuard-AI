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

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/meterguard_db"

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 5000

    # ML Artifacts (relative to PROJECT_ROOT or absolute)
    MODEL1_PATH: str = "models/isolation_forest_final.joblib"
    MODEL2_PATH: str = "models/sih_fault_detection_model_2.joblib"
    ML_ARTIFACTS_DIR: str = "ml/artifacts"

    # Phase 3B: Gemini GenAI Configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

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
