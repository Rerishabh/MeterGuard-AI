"""
MeterGuard AI: LSTM Autoencoder Inference Service
Handles daily (30-step) and hourly (24-step) time-series reconstruction and anomaly scoring.
Enforces rigorous physical validation (non-negativity, numeric sanity, finite values).
Safe fallback: Flask backend will continue running even if models/artifacts are not present.
"""

from pathlib import Path
from datetime import datetime
import json
import math
import pickle
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"

# Global model state
lstm_daily_model = None
lstm_daily_scaler = None
lstm_daily_threshold = None
lstm_daily_available = False

lstm_hourly_model = None
lstm_hourly_scaler = None
lstm_hourly_threshold = None
lstm_hourly_available = False


def init_lstm_models(artifacts_path: Path = None):
    """
    Safely load Daily and Hourly LSTM Autoencoders, scalers, and thresholds.
    Catches all exceptions to prevent crashing the host backend.
    """
    global lstm_daily_model, lstm_daily_scaler, lstm_daily_threshold, lstm_daily_available
    global lstm_hourly_model, lstm_hourly_scaler, lstm_hourly_threshold, lstm_hourly_available

    target_dir = Path(artifacts_path) if artifacts_path else ARTIFACTS_DIR

    print()
    print("==========================================")
    print("    METERGUARD AI: LSTM AE MODEL LOADING  ")
    print("==========================================")

    # 1. Load Daily LSTM Autoencoder (30-step)
    daily_model_path = target_dir / "daily_lstm_autoencoder.keras"
    daily_scaler_path = target_dir / "daily_scaler.pkl"
    daily_thresh_path = target_dir / "daily_threshold.json"

    try:
        if daily_model_path.is_file() and daily_scaler_path.is_file() and daily_thresh_path.is_file():
            import tensorflow as tf

            print("Loading Daily LSTM Autoencoder (30 timesteps)...")
            lstm_daily_model = tf.keras.models.load_model(str(daily_model_path))

            with open(daily_scaler_path, "rb") as f:
                lstm_daily_scaler = pickle.load(f)

            with open(daily_thresh_path, "r") as f:
                lstm_daily_threshold = json.load(f)

            lstm_daily_available = True
            print(f"Daily LSTM Autoencoder loaded successfully! Threshold: {lstm_daily_threshold.get('threshold_95', 'N/A')}")
        else:
            print(f"[WARNING] Daily LSTM Autoencoder artifacts not found at {target_dir}")
            lstm_daily_available = False
    except Exception as e:
        print(f"[ERROR] Failed to load Daily LSTM Autoencoder: {e}")
        lstm_daily_available = False

    # 2. Load Hourly LSTM Autoencoder (24-step)
    hourly_model_path = target_dir / "hourly_lstm_autoencoder.keras"
    hourly_scaler_path = target_dir / "hourly_scaler.pkl"
    hourly_thresh_path = target_dir / "hourly_threshold.json"

    try:
        if hourly_model_path.is_file() and hourly_scaler_path.is_file() and hourly_thresh_path.is_file():
            import tensorflow as tf

            print("Loading Hourly LSTM Autoencoder (24 timesteps)...")
            lstm_hourly_model = tf.keras.models.load_model(str(hourly_model_path))

            with open(hourly_scaler_path, "rb") as f:
                lstm_hourly_scaler = pickle.load(f)

            with open(hourly_thresh_path, "r") as f:
                lstm_hourly_threshold = json.load(f)

            lstm_hourly_available = True
            print(f"Hourly LSTM Autoencoder loaded successfully! Threshold: {lstm_hourly_threshold.get('threshold_95', 'N/A')}")
        else:
            print(f"[WARNING] Hourly LSTM Autoencoder artifacts not found at {target_dir}")
            lstm_hourly_available = False
    except Exception as e:
        print(f"[ERROR] Failed to load Hourly LSTM Autoencoder: {e}")
        lstm_hourly_available = False

    print("==========================================")
    print()


def is_daily_available() -> bool:
    return lstm_daily_available


def is_hourly_available() -> bool:
    return lstm_hourly_available


def validate_consumption_sequence(sequence_type: str, consumption: list) -> tuple:
    """
    Validate input consumption sequence.
    Returns: (is_valid: bool, error_message: str or None)
    """
    if sequence_type not in ["daily", "hourly"]:
        return False, f"Invalid sequence_type '{sequence_type}'. Expected 'daily' (30 values) or 'hourly' (24 values)."

    expected_len = 30 if sequence_type == "daily" else 24

    if not isinstance(consumption, (list, tuple)):
        return False, f"'consumption' must be an array of numeric values, got {type(consumption).__name__}."

    if len(consumption) != expected_len:
        return False, f"Invalid sequence length for {sequence_type}. Expected exactly {expected_len} values, got {len(consumption)}."

    for idx, val in enumerate(consumption):
        if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
            return False, f"Invalid observation at index {idx}: value '{val}' is not a numeric float/int."

        if math.isnan(val) or np.isnan(val):
            return False, f"Invalid observation at index {idx}: NaN (Not a Number) is not allowed."

        if math.isinf(val) or np.isinf(val):
            return False, f"Invalid observation at index {idx}: Infinity is not allowed."

        if val < 0.0:
            return False, f"Invalid observation at index {idx}: Negative consumption ({val} kWh) is physically impossible."

    return True, None


def predict_sequence(sequence_type: str, consumption: list, meter_id: str = "UNKNOWN") -> dict:
    """
    Perform reconstruction inference on a validated consumption sequence.
    sequence_type: 'daily' (30 values) or 'hourly' (24 values)
    consumption: list/array of float non-negative consumption values
    """
    seq_type = sequence_type.lower()
    is_valid, err_msg = validate_consumption_sequence(seq_type, consumption)
    if not is_valid:
        return {
            "status": "error",
            "message": err_msg
        }

    expected_len = 30 if seq_type == "daily" else 24
    is_daily = (seq_type == "daily")
    model = lstm_daily_model if is_daily else lstm_hourly_model
    scaler = lstm_daily_scaler if is_daily else lstm_hourly_scaler
    threshold_meta = lstm_daily_threshold if is_daily else lstm_hourly_threshold
    available = lstm_daily_available if is_daily else lstm_hourly_available

    if not available or model is None or scaler is None or threshold_meta is None:
        return {
            "status": "UNAVAILABLE",
            "message": f"LSTM Autoencoder ({seq_type}) is not available or failed to load.",
            "meter_id": meter_id,
            "sequence_type": seq_type,
            "reconstruction_error": None,
            "threshold": None
        }

    try:
        arr = np.array(consumption, dtype=np.float32).reshape(1, expected_len, 1)

        # Scale with fitted MinMaxScaler
        flat = arr.reshape(-1, 1)
        scaled_flat = scaler.transform(flat)
        scaled = scaled_flat.reshape(1, expected_len, 1)

        # Predict reconstruction
        pred_scaled = model.predict(scaled, verbose=0)

        # Mean Squared Error
        mse = float(np.mean(np.square(scaled - pred_scaled)))

        thresh_val = float(threshold_meta.get("threshold_95", 0.01))
        thresh_99 = float(threshold_meta.get("threshold_99", thresh_val))

        is_anomaly = bool(mse >= thresh_val)
        status = "SUSPICIOUS" if is_anomaly else "NORMAL"

        return {
            "status": status,
            "meter_id": meter_id,
            "sequence_type": seq_type,
            "sequence_length": expected_len,
            "reconstruction_error": round(mse, 6),
            "threshold": round(thresh_val, 6),
            "threshold_99": round(thresh_99, 6),
            "is_anomaly": is_anomaly,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Inference execution error: {str(e)}",
            "meter_id": meter_id,
            "sequence_type": seq_type
        }


def predict_daily_sequence(consumption: list, meter_id: str = "UNKNOWN") -> dict:
    return predict_sequence("daily", consumption, meter_id=meter_id)


def predict_hourly_sequence(consumption: list, meter_id: str = "UNKNOWN") -> dict:
    return predict_sequence("hourly", consumption, meter_id=meter_id)
