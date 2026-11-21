"""
MeterGuard AI: Machine Learning & Decision Engine Service
Encapsulates Model 1 (Isolation Forest), Model 2 (Random Forest),
and Model 3 (Daily & Hourly LSTM Autoencoders).
Strictly preserves feature engineering, calibration constants, temporal filtering,
and decision arbitration logic.
"""

from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
import logging
import math
import joblib
import numpy as np

from backend.app.config import settings, PROJECT_ROOT
from backend.model1_features import create_model1_features
from backend.model2_features import create_model2_features
from backend.decision_logic import get_final_status
from ml.preprocessing.preprocessing import SequenceScaler

logger = logging.getLogger("meterguard.ml_engine")

# =========================================================
# CALIBRATION CONSTANTS (Preserved exactly from Flask app)
# =========================================================
CURRENT_CALIBRATION_FACTOR = 0.005116594394770841
VOLTAGE_CALIBRATION_FACTOR = 0.46046046046046046
CURRENT_ZERO_ADC = 3000.0
REFERENCE_VOLTAGE = 230.0

# =========================================================
# TEMPORAL FILTER & ROLLING COMPRESSION SETTINGS
# =========================================================
PREDICTION_WINDOW = 10
FAULT_CONFIRM_COUNT = 6
NORMAL_CLEAR_COUNT = 5

MODEL1_MIN_HISTORY = 30
PROTOTYPE_DAILY_KWH = 5.0

# =========================================================
# METER METADATA REGISTRY
# =========================================================
METER_LOCATIONS = {
    "M001": {"name": "Meter M001", "latitude": 21.2514, "longitude": 81.6296},
    "M002": {"name": "Meter M002", "latitude": 21.2550, "longitude": 81.6350},
    "M003": {"name": "Meter M003", "latitude": 21.2470, "longitude": 81.6220},
}


class MLEngine:
    """Centralized ML engine handling inference, state tracking, and arbitration."""

    def __init__(self):
        self.model1 = None
        self.model2 = None
        self.daily_lstm = None
        self.hourly_lstm = None
        self.daily_scaler = None
        self.hourly_scaler = None
        self.daily_threshold_meta = None
        self.hourly_threshold_meta = None

        # State stores
        self.meter_history = defaultdict(lambda: deque(maxlen=3000))
        self.live_electrical_history = defaultdict(lambda: deque(maxlen=60))
        self.latest_meter_data: Dict[str, Any] = {}
        self.meter_last_seen: Dict[str, datetime] = {}
        self.model2_prediction_history = defaultdict(lambda: deque(maxlen=10))
        self.fault_state = defaultdict(
            lambda: {
                "active": False,
                "fault_type": None,
                "fault_count": 0,
                "normal_count": 0,
                "confirmed_at": None,
                "last_fault_prediction": None,
            }
        )

    def load_all_models(self):
        """Loads Model 1, Model 2, and Model 3 with graceful degradation."""
        print()
        print("==========================================")
        print("     METERGUARD AI MODEL LOADING")
        print("==========================================")

        # 1. Load Model 1 (Isolation Forest)
        m1_path = settings.get_model1_path()
        try:
            print(f"Loading Model 1 from {m1_path.name}...")
            self.model1 = joblib.load(m1_path)
            print("Model 1 loaded successfully!")
        except Exception as exc:
            logger.error("Failed to load Model 1 from %s: %s", m1_path, exc)
            self.model1 = None

        # 2. Load Model 2 (Random Forest)
        m2_path = settings.get_model2_path()
        try:
            print(f"Loading Model 2 from {m2_path.name}...")
            self.model2 = joblib.load(m2_path)
            print("Model 2 loaded successfully!")
        except Exception as exc:
            logger.error("Failed to load Model 2 from %s: %s", m2_path, exc)
            self.model2 = None

        print("==========================================")
        print("    METERGUARD AI: LSTM AE MODEL LOADING  ")
        print("==========================================")

        # 3. Load Model 3 (Daily & Hourly LSTM Autoencoders)
        artifacts_dir = settings.get_artifacts_dir()
        try:
            import tensorflow as tf
            import json

            # Daily LSTM
            daily_model_path = artifacts_dir / "daily_lstm_autoencoder.keras"
            daily_scaler_path = artifacts_dir / "daily_scaler.pkl"
            daily_thresh_path = artifacts_dir / "daily_threshold.json"

            if daily_model_path.is_file() and daily_scaler_path.is_file() and daily_thresh_path.is_file():
                print("Loading Daily LSTM Autoencoder (30 timesteps)...")
                self.daily_lstm = tf.keras.models.load_model(str(daily_model_path))
                self.daily_scaler = SequenceScaler.load(daily_scaler_path)
                with open(daily_thresh_path, "r") as f:
                    self.daily_threshold_meta = json.load(f)
                active_val = self.daily_threshold_meta.get("active_threshold_value", self.daily_threshold_meta.get("threshold_95"))
                print(f"Daily LSTM Autoencoder loaded successfully! Threshold: {active_val}")
            else:
                logger.warning("Daily LSTM artifacts missing in %s", artifacts_dir)

            # Hourly LSTM
            hourly_model_path = artifacts_dir / "hourly_lstm_autoencoder.keras"
            hourly_scaler_path = artifacts_dir / "hourly_scaler.pkl"
            hourly_thresh_path = artifacts_dir / "hourly_threshold.json"

            if hourly_model_path.is_file() and hourly_scaler_path.is_file() and hourly_thresh_path.is_file():
                print("Loading Hourly LSTM Autoencoder (24 timesteps)...")
                self.hourly_lstm = tf.keras.models.load_model(str(hourly_model_path))
                self.hourly_scaler = SequenceScaler.load(hourly_scaler_path)
                with open(hourly_thresh_path, "r") as f:
                    self.hourly_threshold_meta = json.load(f)
                active_val = self.hourly_threshold_meta.get("active_threshold_value", self.hourly_threshold_meta.get("threshold_95"))
                print(f"Hourly LSTM Autoencoder loaded successfully! Threshold: {active_val}")
            else:
                logger.warning("Hourly LSTM artifacts missing in %s", artifacts_dir)

        except Exception as exc:
            logger.error("Error initializing LSTM models: %s", exc)

        print("==========================================")
        print()

    # ---------------------------------------------------------
    # Helper & Calibration Calculations
    # ---------------------------------------------------------
    def calculate_electrical_values(self, h1_cs: float, h1_vs: float) -> Dict[str, float]:
        current_deviation = abs(float(h1_cs) - CURRENT_ZERO_ADC)
        current_a = max(0.0, current_deviation * CURRENT_CALIBRATION_FACTOR)
        voltage_v = REFERENCE_VOLTAGE
        power_w = voltage_v * current_a

        return {
            "current_A": round(current_a, 3),
            "voltage_V": round(voltage_v, 1),
            "power_W": round(power_w, 2),
            "raw_current_adc": float(h1_cs),
            "raw_voltage_adc": float(h1_vs),
        }

    def get_meter_location(self, meter_id: str) -> Dict[str, Any]:
        if meter_id in METER_LOCATIONS:
            return METER_LOCATIONS[meter_id]
        return {"name": meter_id, "latitude": None, "longitude": None}

    def get_meter_online_status(self, meter_id: str) -> bool:
        if meter_id not in self.meter_last_seen:
            return False
        elapsed = (datetime.now() - self.meter_last_seen[meter_id]).total_seconds()
        return elapsed <= 5

    def get_meter_connection_info(self, meter_id: str) -> Dict[str, Any]:
        """
        Calculates granular meter connectivity based on recent telemetry heartbeat.
        States:
          - ONLINE:  telemetry within last 5 seconds
          - STALE:   telemetry between 5 and 45 seconds ago
          - OFFLINE: no telemetry for > 45 seconds or never observed
        """
        if meter_id not in self.meter_last_seen:
            return {
                "online": False,
                "connection_state": "OFFLINE",
                "last_seen_seconds": None,
                "last_seen": None,
            }

        elapsed = (datetime.now() - self.meter_last_seen[meter_id]).total_seconds()
        if elapsed <= 5:
            state = "ONLINE"
            online = True
        elif elapsed <= 45:
            state = "STALE"
            online = False
        else:
            state = "OFFLINE"
            online = False

        return {
            "online": online,
            "connection_state": state,
            "last_seen_seconds": round(elapsed, 1),
            "last_seen": self.meter_last_seen[meter_id].isoformat(),
        }

    def normalize_model2_prediction(self, prediction: Any) -> str:
        pred_str = str(prediction).strip().upper()
        if pred_str in ["NORMAL", "FAULT_S1", "FAULT_S2", "FAULT"]:
            return pred_str
        if pred_str in ["1", "1.0"]:
            return "NORMAL"
        if pred_str in ["-1", "-1.0"]:
            return "FAULT"
        return pred_str

    # ---------------------------------------------------------
    # Temporal Filter Logic
    # ---------------------------------------------------------
    def update_fault_filter(self, meter_id: str, raw_prediction: str) -> Dict[str, Any]:
        state = self.fault_state[meter_id]
        history = self.model2_prediction_history[meter_id]
        history.append(raw_prediction)

        normal_count = history.count("NORMAL")
        fault_s1_count = history.count("FAULT_S1")
        fault_s2_count = history.count("FAULT_S2")
        generic_fault_count = history.count("FAULT")

        if fault_s1_count >= fault_s2_count:
            specific_fault = "FAULT_S1"
            specific_count = fault_s1_count
        else:
            specific_fault = "FAULT_S2"
            specific_count = fault_s2_count

        # ACTIVE FAULT branch
        if state["active"]:
            state["normal_count"] = (state["normal_count"] + 1) if raw_prediction == "NORMAL" else 0
            if raw_prediction == state["fault_type"]:
                state["fault_count"] += 1

            # Clear only after 5 consecutive NORMAL readings
            if state["normal_count"] >= NORMAL_CLEAR_COUNT:
                print(f"[FAULT CLEARED] {meter_id} -> {state['fault_type']}")
                cleared_fault = state["fault_type"]
                state["active"] = False
                state["fault_type"] = None
                state["fault_count"] = 0
                state["normal_count"] = 0
                state["confirmed_at"] = None
                state["last_fault_prediction"] = None

                return {
                    "prediction": "NORMAL",
                    "raw_prediction": raw_prediction,
                    "fault_active": False,
                    "fault_type": None,
                    "window_size": len(history),
                    "normal_count": normal_count,
                    "fault_s1_count": fault_s1_count,
                    "fault_s2_count": fault_s2_count,
                    "fault_confidence": 0.0,
                    "fault_status": "CLEARED",
                }

            # Still active
            return {
                "prediction": state["fault_type"],
                "raw_prediction": raw_prediction,
                "fault_active": True,
                "fault_type": state["fault_type"],
                "window_size": len(history),
                "normal_count": normal_count,
                "fault_s1_count": fault_s1_count,
                "fault_s2_count": fault_s2_count,
                "fault_confidence": round((specific_count / max(1, len(history))) * 100, 1),
                "fault_status": "CONFIRMED",
            }

        # NO ACTIVE FAULT branch
        state["normal_count"] = (state["normal_count"] + 1) if raw_prediction == "NORMAL" else 0

        if specific_count >= FAULT_CONFIRM_COUNT:
            state["active"] = True
            state["fault_type"] = specific_fault
            state["fault_count"] = specific_count
            state["normal_count"] = 0
            state["confirmed_at"] = datetime.now().isoformat()
            state["last_fault_prediction"] = raw_prediction
            print(f"[FAULT CONFIRMED] {meter_id} -> {specific_fault}")

            return {
                "prediction": specific_fault,
                "raw_prediction": raw_prediction,
                "fault_active": True,
                "fault_type": specific_fault,
                "window_size": len(history),
                "normal_count": normal_count,
                "fault_s1_count": fault_s1_count,
                "fault_s2_count": fault_s2_count,
                "fault_confidence": round((specific_count / max(1, len(history))) * 100, 1),
                "fault_status": "CONFIRMED",
            }

        if generic_fault_count >= FAULT_CONFIRM_COUNT:
            state["active"] = True
            state["fault_type"] = "ELECTRICAL_FAULT"
            state["fault_count"] = generic_fault_count
            state["normal_count"] = 0
            state["confirmed_at"] = datetime.now().isoformat()

            return {
                "prediction": "ELECTRICAL_FAULT",
                "raw_prediction": raw_prediction,
                "fault_active": True,
                "fault_type": "ELECTRICAL_FAULT",
                "window_size": len(history),
                "normal_count": normal_count,
                "fault_s1_count": fault_s1_count,
                "fault_s2_count": fault_s2_count,
                "fault_confidence": round((generic_fault_count / max(1, len(history))) * 100, 1),
                "fault_status": "CONFIRMED",
            }

        return {
            "prediction": "NORMAL",
            "raw_prediction": raw_prediction,
            "fault_active": False,
            "fault_type": None,
            "window_size": len(history),
            "normal_count": normal_count,
            "fault_s1_count": fault_s1_count,
            "fault_s2_count": fault_s2_count,
            "fault_confidence": round((specific_count / max(1, len(history))) * 100, 1),
            "fault_status": "MONITORING",
        }

    # ---------------------------------------------------------
    # Model 1 Consumption & Inference
    # ---------------------------------------------------------
    def generate_model1_consumption(self, meter_id: str) -> Optional[np.ndarray]:
        history = self.meter_history[meter_id]
        if len(history) < MODEL1_MIN_HISTORY:
            return None

        values = np.array(history, dtype=float)
        baseline = np.median(values)
        signal = np.abs(values - baseline)

        if signal.mean() <= 0:
            return np.zeros(30)

        chunks = np.array_split(signal, 30)
        daily_signal = [0.0 if len(c) == 0 else float(np.mean(c)) for c in chunks]
        daily_signal = np.array(daily_signal, dtype=float)

        profile_mean = daily_signal.mean()
        if profile_mean <= 0:
            return np.zeros(30)

        consumption = (daily_signal / profile_mean) * PROTOTYPE_DAILY_KWH
        return np.clip(consumption, 0, None)

    def run_model1(self, meter_id: str) -> Dict[str, Any]:
        if self.model1 is None:
            return {
                "prediction": "UNAVAILABLE",
                "raw_prediction": None,
                "history_length": len(self.meter_history[meter_id]),
                "features": None,
                "consumption_history": None,
            }

        consumption = self.generate_model1_consumption(meter_id)
        if consumption is None:
            hist_len = len(self.meter_history[meter_id])
            pred_state = "WAITING FOR DATA" if hist_len == 0 else "INSUFFICIENT HISTORY"
            return {
                "prediction": pred_state,
                "status_code": "INSUFFICIENT_HISTORY",
                "message": f"Awaiting sufficient 30-day consumption history ({hist_len}/30 readings collected).",
                "raw_prediction": None,
                "history_length": hist_len,
                "required_length": MODEL1_MIN_HISTORY,
                "features": None,
                "consumption_history": None,
            }

        features = create_model1_features(consumption)
        raw_pred = self.model1.predict(features)[0]

        if raw_pred == 1:
            pred = "NORMAL"
        elif raw_pred == -1:
            pred = "SUSPICIOUS"
        else:
            pred = "UNKNOWN"

        feature_dict = {col: float(features.iloc[0][col]) for col in features.columns}
        return {
            "prediction": pred,
            "raw_prediction": int(raw_pred),
            "history_length": len(self.meter_history[meter_id]),
            "features": feature_dict,
            "consumption_history": [round(float(v), 3) for v in consumption],
        }

    def evaluate_consumption_with_model1(self, consumption: Any) -> Optional[Dict[str, Any]]:
        """
        Runs Model 1 Isolation Forest directly on an authentic 30-day daily consumption sequence
        without fabricating numbers.
        """
        if self.model1 is None:
            return None
        if not isinstance(consumption, (list, tuple, np.ndarray)) or len(consumption) != 30:
            return None
        try:
            features = create_model1_features(consumption)
            raw_pred = self.model1.predict(features)[0]
            pred = "NORMAL" if raw_pred == 1 else ("SUSPICIOUS" if raw_pred == -1 else "UNKNOWN")
            feature_dict = {col: float(features.iloc[0][col]) for col in features.columns}
            return {
                "prediction": pred,
                "raw_prediction": int(raw_pred),
                "history_length": 30,
                "required_length": 30,
                "features": feature_dict,
                "consumption_history": [round(float(v), 3) for v in consumption],
            }
        except Exception as exc:
            logger.warning("Error evaluating consumption with Model 1: %s", exc)
            return None

    # ---------------------------------------------------------
    # Sequential LSTM Anomaly Detection (Model 3)
    # ---------------------------------------------------------
    def validate_consumption_sequence(self, sequence_type: str, consumption: Any) -> Tuple[bool, Optional[str]]:
        if sequence_type not in ["daily", "hourly"]:
            return False, f"Invalid sequence_type '{sequence_type}'. Expected 'daily' (30 values) or 'hourly' (24 values)."

        expected_length = 30 if sequence_type == "daily" else 24

        if not isinstance(consumption, (list, tuple, np.ndarray)):
            return False, f"'consumption' must be an array of numeric values. Received: {type(consumption).__name__}"

        if len(consumption) != expected_length:
            return False, f"Invalid sequence length for {sequence_type}. Expected exactly {expected_length} values, got {len(consumption)}."

        for idx, val in enumerate(consumption):
            if val is None or isinstance(val, (bool, str)):
                return False, f"Invalid observation at index {idx}: value '{val}' is not a numeric float/int."
            try:
                fval = float(val)
            except (ValueError, TypeError):
                return False, f"Invalid observation at index {idx}: '{val}' cannot be parsed as a float."

            if math.isnan(fval):
                return False, f"Invalid observation at index {idx}: NaN (Not a Number) is not allowed."
            if math.isinf(fval):
                return False, f"Invalid observation at index {idx}: Infinity is not allowed."
            if fval < 0.0:
                return False, f"Invalid observation at index {idx}: Negative consumption ({fval} kWh) is physically impossible."

        return True, None

    def predict_sequence(self, sequence_type: str, consumption: List[float], meter_id: str = "UNKNOWN") -> Dict[str, Any]:
        model = self.daily_lstm if sequence_type == "daily" else self.hourly_lstm
        scaler = self.daily_scaler if sequence_type == "daily" else self.hourly_scaler
        thresh_meta = self.daily_threshold_meta if sequence_type == "daily" else self.hourly_threshold_meta

        # Attempt on-demand load if models were not initialized via lifespan
        if model is None or scaler is None or thresh_meta is None:
            self.load_all_models()
            model = self.daily_lstm if sequence_type == "daily" else self.hourly_lstm
            scaler = self.daily_scaler if sequence_type == "daily" else self.hourly_scaler
            thresh_meta = self.daily_threshold_meta if sequence_type == "daily" else self.hourly_threshold_meta

        if model is None or scaler is None or thresh_meta is None:
            return {
                "status": "error",
                "message": f"{sequence_type.capitalize()} LSTM Autoencoder model or calibration artifacts unavailable.",
                "meter_id": meter_id,
            }

        seq_arr = np.array(consumption, dtype=np.float32).reshape(1, -1, 1)
        seq_scaled = scaler.transform(seq_arr)
        pred_scaled = model.predict(seq_scaled, verbose=0)

        # MSE reconstruction error
        mse_error = float(np.mean(np.square(seq_scaled - pred_scaled)))
        active_thresh = float(thresh_meta.get("active_threshold_value", thresh_meta.get("threshold_95", 0.01)))
        threshold_99 = float(thresh_meta.get("threshold_99", active_thresh * 1.5))
        is_anomaly = bool(mse_error >= active_thresh)

        return {
            "status": "SUSPICIOUS" if is_anomaly else "NORMAL",
            "meter_id": meter_id,
            "sequence_type": sequence_type,
            "sequence_length": len(consumption),
            "reconstruction_error": round(mse_error, 6),
            "threshold": round(active_thresh, 6),
            "threshold_99": round(threshold_99, 6),
            "is_anomaly": is_anomaly,
            "timestamp": datetime.now().isoformat(),
        }


# Global singleton instance
ml_engine = MLEngine()
