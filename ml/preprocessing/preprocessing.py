"""
MeterGuard AI: Preprocessing & Scaler Module
Fits normalizers exclusively on normal training sequences to prevent data leakage.
"""

from pathlib import Path
import pickle
import numpy as np
from sklearn.preprocessing import MinMaxScaler

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"


class SequenceScaler:
    """
    MinMaxScaler wrapper designed for 3D time-series arrays (batch, timesteps, 1).
    Fitted exclusively on normal training data.
    """
    def __init__(self, feature_range=(0, 1)):
        self.scaler = MinMaxScaler(feature_range=feature_range)
        self.is_fitted = False

    def fit(self, X: np.ndarray):
        """Fit scaler on training data. X shape: (N, timesteps) or (N, timesteps, 1)."""
        flat = X.reshape(-1, 1)
        self.scaler.fit(flat)
        self.is_fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform X using the fitted scaler."""
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fitted before transforming data.")
        orig_shape = X.shape
        flat = X.reshape(-1, 1)
        scaled_flat = self.scaler.transform(flat)
        return scaled_flat.reshape(orig_shape)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        orig_shape = X.shape
        flat = X.reshape(-1, 1)
        unscaled = self.scaler.inverse_transform(flat)
        return unscaled.reshape(orig_shape)

    def save(self, filepath: Path):
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(self.scaler, f)

    @classmethod
    def load(cls, filepath: Path):
        filepath = Path(filepath)
        if not filepath.is_file():
            raise FileNotFoundError(f"Scaler file not found at: {filepath}")
        instance = cls()
        with open(filepath, "rb") as f:
            instance.scaler = pickle.load(f)
        instance.is_fitted = True
        return instance
