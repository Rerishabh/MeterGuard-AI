"""
Phase C: AI Tampering Detection Investigation Runner
Evaluates all four ML models across the 6 tampering scenarios:
1. Model 1: Isolation Forest (30-day consumption)
2. Model 2: Random Forest (real-time electrical telemetry)
3. Model 3 Daily: 30-day Daily LSTM Autoencoder
4. Model 3 Hourly: 24-hour Hourly LSTM Autoencoder
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.ml_engine import ml_engine
from backend.app.services.tamper_simulator import tamper_simulator, VALID_SCENARIOS
from backend.model1_features import create_model1_features, MODEL1_FEATURES
from backend.model2_features import create_model2_features, FEATURE_LIST as MODEL2_FEATURES
from backend.decision_logic import get_final_status


def evaluate_all():
    print("=" * 80)
    print("      METERGUARD AI: PHASE C - AI TAMPERING DETECTION INVESTIGATION      ")
    print("=" * 80)

    # 1. Load All Models
    ml_engine.load_all_models()

    print("\n--- 1. MODEL ARCHITECTURE & INPUT ARTIFACTS ---")
    print(f"Model 1 (Isolation Forest): {type(ml_engine.model1)}")
    if ml_engine.model1:
        print(f"   Features (7): {MODEL1_FEATURES}")
        print(f"   Contamination: {getattr(ml_engine.model1, 'contamination', 'auto')}")
        print(f"   Estimators: {len(getattr(ml_engine.model1, 'estimators_', []))}")

    print(f"\nModel 2 (Random Forest): {type(ml_engine.model2)}")
    if ml_engine.model2:
        print(f"   Features (12): {MODEL2_FEATURES}")
        print(f"   Classes: {getattr(ml_engine.model2, 'classes_', [])}")
        print(f"   Estimators: {len(getattr(ml_engine.model2, 'estimators_', []))}")

    print(f"\nModel 3 Daily (LSTM Autoencoder): {type(ml_engine.daily_lstm)}")
    if ml_engine.daily_lstm:
        print(f"   Input Shape: {ml_engine.daily_lstm.input_shape} (Batch, 30, 1)")
        print(f"   Threshold: {ml_engine.daily_threshold_meta.get('active_threshold_value')} (Threshold 99: {ml_engine.daily_threshold_meta.get('threshold_99')})")
        if ml_engine.daily_scaler and hasattr(ml_engine.daily_scaler, "scaler"):
            inner = ml_engine.daily_scaler.scaler
            print(f"   Daily Scaler Type: {type(inner).__name__}")
            if hasattr(inner, "data_min_") and hasattr(inner, "data_max_"):
                print(f"   Scaler Fitted Range: min={inner.data_min_}, max={inner.data_max_}")

    print(f"\nModel 3 Hourly (LSTM Autoencoder): {type(ml_engine.hourly_lstm)}")
    if ml_engine.hourly_lstm:
        print(f"   Input Shape: {ml_engine.hourly_lstm.input_shape} (Batch, 24, 1)")
        print(f"   Threshold: {ml_engine.hourly_threshold_meta.get('active_threshold_value')} (Threshold 99: {ml_engine.hourly_threshold_meta.get('threshold_99')})")
        if ml_engine.hourly_scaler and hasattr(ml_engine.hourly_scaler, "scaler"):
            inner = ml_engine.hourly_scaler.scaler
            print(f"   Hourly Scaler Type: {type(inner).__name__}")
            if hasattr(inner, "data_min_") and hasattr(inner, "data_max_"):
                print(f"   Scaler Fitted Range: min={inner.data_min_}, max={inner.data_max_}")

    # 2. Detailed Evaluation of the 6 Scenarios across Model 1 and Model 3 Daily
    print("\n" + "=" * 80)
    print("--- 2. DETAILED SIX-SCENARIO EVALUATION (DAILY 30-DAY SEQUENCES) ---")
    print("=" * 80)

    scenario_results = {}
    detailed_tables = []

    for sc in VALID_SCENARIOS:
        print(f"\n>>> Scenario: {sc.upper()} ({VALID_SCENARIOS[sc]})")
        seq = tamper_simulator.generate_sequence(sc)
        arr = np.array(seq)

        # A. Raw Metrics
        min_kwh = float(np.min(arr))
        max_kwh = float(np.max(arr))
        mean_kwh = float(np.mean(arr))
        std_kwh = float(np.std(arr))
        print(f"   Raw 30-Day Sequence: Min={min_kwh:.3f}, Max={max_kwh:.3f}, Mean={mean_kwh:.3f}, Std={std_kwh:.3f}")

        # B. Model 1 (Isolation Forest)
        m1_features = create_model1_features(seq)
        m1_dict = {col: round(float(m1_features.iloc[0][col]), 4) for col in m1_features.columns}
        raw_m1_pred = int(ml_engine.model1.predict(m1_features)[0])
        m1_score = float(ml_engine.model1.decision_function(m1_features)[0])
        m1_verdict = "NORMAL" if raw_m1_pred == 1 else "SUSPICIOUS"
        print(f"   Model 1 (IF): Pred={raw_m1_pred} ({m1_verdict}), Decision Score={m1_score:.4f}")
        print(f"      Features: {m1_dict}")

        # C. Model 3 Daily (LSTM Autoencoder)
        seq_input = arr.reshape(1, -1, 1)
        seq_scaled = ml_engine.daily_scaler.transform(seq_input)
        pred_scaled = ml_engine.daily_lstm.predict(seq_scaled, verbose=0)

        # Per-timestep squared differences
        sq_diffs = np.square(seq_scaled - pred_scaled)[0, :, 0]
        daily_mse = float(np.mean(sq_diffs))
        daily_thresh = float(ml_engine.daily_threshold_meta.get("active_threshold_value", 0.013009))
        daily_anomaly = bool(daily_mse >= daily_thresh)
        daily_verdict = "SUSPICIOUS" if daily_anomaly else "NORMAL"

        max_timestep_err = float(np.max(sq_diffs))
        max_err_day = int(np.argmax(sq_diffs))

        print(f"   Model 3 Daily (LSTM): MSE={daily_mse:.6f} vs Thresh={daily_thresh:.6f} -> {daily_verdict}")
        print(f"      Max Timestep Error: Day {max_err_day + 1} Error={max_timestep_err:.6f}")
        print(f"      Scaled Range: Min={float(np.min(seq_scaled)):.4f}, Max={float(np.max(seq_scaled)):.4f}")

        scenario_results[sc] = {
            "min_kwh": round(min_kwh, 3),
            "max_kwh": round(max_kwh, 3),
            "mean_kwh": round(mean_kwh, 3),
            "std_kwh": round(std_kwh, 3),
            "m1_features": m1_dict,
            "m1_pred": raw_m1_pred,
            "m1_score": round(m1_score, 4),
            "m1_verdict": m1_verdict,
            "daily_mse": round(daily_mse, 6),
            "daily_thresh": round(daily_thresh, 6),
            "daily_verdict": daily_verdict,
            "daily_is_anomaly": daily_anomaly,
            "max_timestep_err": round(max_timestep_err, 6),
            "max_err_day": max_err_day + 1,
        }

    # 3. Model 3 Hourly LSTM Evaluation on Intraday Patterns
    print("\n" + "=" * 80)
    print("--- 3. MODEL 3 HOURLY LSTM AUTOENCODER EVALUATION (24-HOUR SEQUENCES) ---")
    print("=" * 80)

    # Hourly Baseline: Standard diurnal profile (~0.2 kWh base, peaking at 0.6 kWh evening)
    rng = np.random.default_rng(42)
    hour_of_day = np.arange(24)
    # Diurnal wave peaking at 20:00 (hour 20)
    diurnal_curve = 0.2 + 0.3 * np.exp(-0.5 * ((hour_of_day - 20) / 3.0) ** 2) + 0.15 * np.exp(-0.5 * ((hour_of_day - 8) / 2.0) ** 2)

    hourly_scenarios = {}
    # A. Normal Hourly
    h_normal = np.clip(diurnal_curve + rng.normal(0, 0.03, size=24), 0.05, 1.0)
    # B. Night Tamper (abnormally low night on hourly resolution: hours 0-6 suppressed to ~0.01 kWh)
    h_night_tamper = h_normal.copy()
    h_night_tamper[0:6] = 0.01  # Direct 95% diversion during night hours
    # C. Hourly Peak Spike (sudden 2.5 kWh surge at hour 14)
    h_spike = h_normal.copy()
    h_spike[14:17] = 2.8
    # D. Inversion Hourly (high night, zero day)
    h_inversion = np.roll(h_normal, 12)

    hourly_tests = {
        "hourly_normal": h_normal,
        "hourly_abnormally_low_night": h_night_tamper,
        "hourly_spike": h_spike,
        "hourly_inversion": h_inversion,
    }

    for h_name, h_seq in hourly_tests.items():
        res_h = ml_engine.predict_sequence("hourly", list(h_seq))
        mse_h = res_h["reconstruction_error"]
        thresh_h = res_h["threshold"]
        verdict_h = res_h["status"]
        print(f"Hourly [{h_name}]: MSE={mse_h:.6f} vs Thresh={thresh_h:.6f} -> {verdict_h} (Anomaly: {res_h['is_anomaly']})")
        hourly_scenarios[h_name] = {
            "mse": round(mse_h, 6),
            "threshold": round(thresh_h, 6),
            "verdict": verdict_h,
            "is_anomaly": res_h["is_anomaly"],
        }

    # 4. Model 2 (Random Forest) Evaluation on Physical Electrical Tamper Frames
    print("\n" + "=" * 80)
    print("--- 4. MODEL 2 (RANDOM FOREST) REAL-TIME ELECTRICAL HARDWARE EVALUATION ---")
    print("=" * 80)

    electrical_cases = [
        {
            "name": "Normal Balanced Load",
            "readings": {"T1_CS": 3025.4, "T1_VS": 230.1, "T2_CS": 3025.0, "T2_VS": 230.0, "H1_CS": 3025.4, "H1_VS": 230.1},
        },
        {
            "name": "Line-Tap / Bypass Fault (S1)",
            "readings": {"T1_CS": 3080.0, "T1_VS": 230.0, "T2_CS": 3020.0, "T2_VS": 230.0, "H1_CS": 3010.0, "H1_VS": 230.0},
        },
        {
            "name": "Neutral Cut Bypass (S2)",
            "readings": {"T1_CS": 3020.0, "T1_VS": 230.0, "T2_CS": 3020.0, "T2_VS": 230.0, "H1_CS": 3000.0, "H1_VS": 115.0},
        },
    ]

    model2_eval_results = []
    for ec in electrical_cases:
        X2 = create_model2_features(ec["readings"])
        pred2 = ml_engine.model2.predict(X2)[0]
        probs2 = ml_engine.model2.predict_proba(X2)[0]
        classes = list(ml_engine.model2.classes_)
        prob_dict = {classes[i]: round(float(probs2[i]), 3) for i in range(len(classes))}
        print(f"Electrical Case [{ec['name']}]: Predicted={pred2} | Probabilities={prob_dict}")
        model2_eval_results.append({
            "name": ec["name"],
            "prediction": pred2,
            "probabilities": prob_dict,
        })

    return {
        "daily_scenarios": scenario_results,
        "hourly_scenarios": hourly_scenarios,
        "model2_eval": model2_eval_results,
    }


if __name__ == "__main__":
    out = evaluate_all()
    out_file = PROJECT_ROOT / "phase_c_evaluation_results.json"
    with open(out_file, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[DONE] Detailed Phase C metrics saved to {out_file}")
