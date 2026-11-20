"""
MeterGuard AI: Data Loader Module
Loads and validates synthetic and raw smart-meter time-series datasets.
"""

from pathlib import Path
from typing import Tuple
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SYNTHETIC_DIR = PROJECT_ROOT / "ml" / "dataset" / "synthetic"
RAW_DIR = PROJECT_ROOT / "ml" / "dataset" / "raw"


def load_dataset(dataset_type: str = "daily", csv_path: Path = None) -> pd.DataFrame:
    """
    Load daily or hourly dataset from CSV.
    Validates required columns and clean types.
    """
    if csv_path is None:
        if dataset_type == "daily":
            csv_path = SYNTHETIC_DIR / "synthetic_daily_consumption.csv"
        elif dataset_type == "hourly":
            csv_path = SYNTHETIC_DIR / "synthetic_hourly_consumption.csv"
        else:
            raise ValueError(f"Unknown dataset_type: {dataset_type}. Must be 'daily' or 'hourly'.")

    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found at: {path}")

    df = pd.read_csv(path)
    required_cols = ["sequence_id", "meter_id", "timestep", "consumption", "is_anomaly", "anomaly_type"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns {missing} in dataset: {path}")

    # Sanitize invalid / negative values
    df["consumption"] = df["consumption"].clip(lower=0.0)
    df = df.dropna(subset=["consumption"])

    return df
