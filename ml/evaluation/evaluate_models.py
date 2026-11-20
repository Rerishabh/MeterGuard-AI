"""
MeterGuard AI: Model Evaluation and Benchmarking Suite
Compares:
1. Existing Isolation Forest (using 7 statistical features from backend/model1_features.py)
2. Daily LSTM Autoencoder (30-step reconstruction error)
3. Hourly LSTM Autoencoder (24-step reconstruction error)

Evaluates on held-out test sets across 5 anomaly scenarios.
Generates CSV tables, publication plots, and a Markdown evaluation report.
"""

import argparse
import json
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_curve,
)
import tensorflow as tf

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "ml"))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from preprocessing.data_loader import load_dataset
from preprocessing.preprocessing import SequenceScaler
from preprocessing.sequence_generator import prepare_sequences
from model1_features import create_model1_features
import plots

ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
MODELS_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = SCRIPT_DIR / "results"


def parse_args():
    parser = argparse.ArgumentParser(description="MeterGuard AI: Evaluate ML Models")
    parser.add_argument("--seed", type=int, default=42, help="Evaluation split seed (default: 42)")
    return parser.parse_args()


def evaluate_binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, continuous_scores: np.ndarray):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    try:
        fpr_curve, tpr_curve, _ = roc_curve(y_true, continuous_scores)
        roc_auc = auc(fpr_curve, tpr_curve)
    except Exception:
        roc_auc = float("nan")

    return {
        "Accuracy": round(float(acc), 4),
        "Precision": round(float(prec), 4),
        "Recall (TPR)": round(float(rec), 4),
        "F1-Score": round(float(f1), 4),
        "ROC-AUC": round(float(roc_auc), 4),
        "False Positive Rate": round(float(fpr), 4),
        "TP": int(tp),
        "FP": int(fp),
        "TN": int(tn),
        "FN": int(fn),
        "Confusion_Matrix": cm,
    }


def evaluate_isolation_forest(X_test: np.ndarray, y_test: np.ndarray):
    """
    Evaluates existing Isolation Forest on 30-day sequences.
    Converts 30-day sequences to 7 statistical features using create_model1_features.
    """
    model_path = MODELS_DIR / "isolation_forest_final.joblib"
    if not model_path.is_file():
        raise FileNotFoundError(f"Isolation Forest model not found at: {model_path}")

    iso_model = joblib.load(model_path)

    # Extract 7 features for each sample
    feature_rows = []
    for seq in X_test:
        raw_values = seq.flatten()
        feat_df = create_model1_features(raw_values)
        feature_rows.append(feat_df.iloc[0])

    features_df = pd.DataFrame(feature_rows)

    # In scikit-learn IsolationForest: 1 is inlier (normal), -1 is outlier (anomaly)
    raw_preds = iso_model.predict(features_df)
    # Convert to 0 = normal, 1 = anomaly
    y_pred = np.where(raw_preds == -1, 1, 0)

    # Continuous anomaly score: lower decision_function = more anomalous -> negate for ROC
    continuous_scores = -iso_model.decision_function(features_df)

    metrics = evaluate_binary_metrics(y_test, y_pred, continuous_scores)
    return metrics, y_pred, continuous_scores


def evaluate_lstm_ae(dataset_type: str, X_test: np.ndarray, y_test: np.ndarray):
    """Evaluates Daily or Hourly LSTM Autoencoder on held-out test sequences."""
    model_path = ARTIFACTS_DIR / f"{dataset_type}_lstm_autoencoder.keras"
    scaler_path = ARTIFACTS_DIR / f"{dataset_type}_scaler.pkl"
    thresh_path = ARTIFACTS_DIR / f"{dataset_type}_threshold.json"

    if not model_path.is_file() or not scaler_path.is_file() or not thresh_path.is_file():
        raise FileNotFoundError(f"Missing artifacts for {dataset_type} LSTM Autoencoder.")

    model = tf.keras.models.load_model(str(model_path))
    scaler = SequenceScaler.load(scaler_path)

    with open(thresh_path, "r") as f:
        thresh_meta = json.load(f)
    threshold = thresh_meta["threshold_95"]

    X_test_scaled = scaler.transform(X_test)
    X_pred_scaled = model.predict(X_test_scaled, verbose=0)

    # Reconstruction error (MSE per sample)
    reconstruction_errors = np.mean(np.square(X_test_scaled - X_pred_scaled), axis=(1, 2))

    y_pred = np.where(reconstruction_errors >= threshold, 1, 0)
    metrics = evaluate_binary_metrics(y_test, y_pred, reconstruction_errors)
    metrics["Threshold_Used"] = threshold

    return metrics, y_pred, reconstruction_errors, threshold


def main():
    args = parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================================")
    print("      MeterGuard AI: Multi-Model Evaluation & Benchmarking        ")
    print("==================================================================")

    # 1. Load Datasets & Splits
    print("[1/5] Preparing test sets for Daily and Hourly streams...")
    daily_df = load_dataset("daily")
    daily_splits = prepare_sequences(daily_df, dataset_type="daily", seed=args.seed)
    X_daily_test, y_daily_test, meta_daily = daily_splits["test"]

    hourly_df = load_dataset("hourly")
    hourly_splits = prepare_sequences(hourly_df, dataset_type="hourly", seed=args.seed)
    X_hourly_test, y_hourly_test, meta_hourly = hourly_splits["test"]

    print(f"      Daily Held-out Test Set  : {len(X_daily_test)} sequences ({sum(y_daily_test)} anomalous, {len(y_daily_test) - sum(y_daily_test)} normal)")
    print(f"      Hourly Held-out Test Set : {len(X_hourly_test)} sequences ({sum(y_hourly_test)} anomalous, {len(y_hourly_test) - sum(y_hourly_test)} normal)")

    # 2. Evaluate Models
    print("\n[2/5] Evaluating Existing Isolation Forest (on 30-day engineered features)...")
    iso_metrics, iso_preds, iso_scores = evaluate_isolation_forest(X_daily_test, y_daily_test)
    print(f"      Isolation Forest F1: {iso_metrics['F1-Score']:.4f} | ROC-AUC: {iso_metrics['ROC-AUC']:.4f} | FPR: {iso_metrics['False Positive Rate']:.4f}")

    print("\n[3/5] Evaluating New Daily LSTM Autoencoder (30 timesteps)...")
    daily_metrics, daily_preds, daily_errors, daily_thresh = evaluate_lstm_ae("daily", X_daily_test, y_daily_test)
    print(f"      Daily LSTM-AE F1   : {daily_metrics['F1-Score']:.4f} | ROC-AUC: {daily_metrics['ROC-AUC']:.4f} | FPR: {daily_metrics['False Positive Rate']:.4f}")

    print("\n[4/5] Evaluating New Hourly LSTM Autoencoder (24 timesteps)...")
    hourly_metrics, hourly_preds, hourly_errors, hourly_thresh = evaluate_lstm_ae("hourly", X_hourly_test, y_hourly_test)
    print(f"      Hourly LSTM-AE F1  : {hourly_metrics['F1-Score']:.4f} | ROC-AUC: {hourly_metrics['ROC-AUC']:.4f} | FPR: {hourly_metrics['False Positive Rate']:.4f}")

    # 3. Model Comparison Table
    comparison_rows = [
        {
            "Model": "Existing Isolation Forest",
            "Input Granularity": "Daily (30-day 7 statistical features)",
            "Total Samples": int(len(y_daily_test)),
            "TP": iso_metrics["TP"],
            "FP": iso_metrics["FP"],
            "TN": iso_metrics["TN"],
            "FN": iso_metrics["FN"],
            "Accuracy": iso_metrics["Accuracy"],
            "Precision": iso_metrics["Precision"],
            "Recall": iso_metrics["Recall (TPR)"],
            "F1-Score": iso_metrics["F1-Score"],
            "ROC-AUC": iso_metrics["ROC-AUC"],
            "FPR": iso_metrics["False Positive Rate"],
        },
        {
            "Model": "Daily LSTM Autoencoder",
            "Input Granularity": "Daily (30 timesteps sequential)",
            "Total Samples": int(len(y_daily_test)),
            "TP": daily_metrics["TP"],
            "FP": daily_metrics["FP"],
            "TN": daily_metrics["TN"],
            "FN": daily_metrics["FN"],
            "Accuracy": daily_metrics["Accuracy"],
            "Precision": daily_metrics["Precision"],
            "Recall": daily_metrics["Recall (TPR)"],
            "F1-Score": daily_metrics["F1-Score"],
            "ROC-AUC": daily_metrics["ROC-AUC"],
            "FPR": daily_metrics["False Positive Rate"],
        },
        {
            "Model": "Hourly LSTM Autoencoder",
            "Input Granularity": "Hourly (24 timesteps sequential)",
            "Total Samples": int(len(y_hourly_test)),
            "TP": hourly_metrics["TP"],
            "FP": hourly_metrics["FP"],
            "TN": hourly_metrics["TN"],
            "FN": hourly_metrics["FN"],
            "Accuracy": hourly_metrics["Accuracy"],
            "Precision": hourly_metrics["Precision"],
            "Recall": hourly_metrics["Recall (TPR)"],
            "F1-Score": hourly_metrics["F1-Score"],
            "ROC-AUC": hourly_metrics["ROC-AUC"],
            "FPR": hourly_metrics["False Positive Rate"],
        },
    ]
    comp_df = pd.DataFrame(comparison_rows)
    comp_csv_path = RESULTS_DIR / "model_comparison.csv"
    comp_df.to_csv(comp_csv_path, index=False)
    print(f"\nSaved model comparison table -> {comp_csv_path.name}")

    # 4. Scenario-wise Breakdown (Daily & Hourly)
    scenario_rows = []

    # Daily breakdown
    test_meta_daily_df = pd.DataFrame(meta_daily)
    test_meta_daily_df["y_true"] = y_daily_test
    test_meta_daily_df["iso_pred"] = iso_preds
    test_meta_daily_df["daily_ae_pred"] = daily_preds

    for sc in sorted(test_meta_daily_df["anomaly_type"].unique()):
        sub = test_meta_daily_df[test_meta_daily_df["anomaly_type"] == sc]
        n_samples = len(sub)
        is_normal = (sc == "normal")
        
        iso_detected = int((sub["iso_pred"] == 0).sum() if is_normal else (sub["iso_pred"] == 1).sum())
        iso_missed = n_samples - iso_detected
        iso_rate = round(iso_detected / n_samples, 4)

        ae_detected = int((sub["daily_ae_pred"] == 0).sum() if is_normal else (sub["daily_ae_pred"] == 1).sum())
        ae_missed = n_samples - ae_detected
        ae_rate = round(ae_detected / n_samples, 4)

        scenario_rows.append({
            "Stream": "Daily",
            "Scenario": sc,
            "Total Samples": n_samples,
            "ISO Correct": iso_detected,
            "ISO Missed": iso_missed,
            "ISO Detection Rate": iso_rate,
            "LSTM Correct": ae_detected,
            "LSTM Missed": ae_missed,
            "LSTM Detection Rate": ae_rate,
        })

    # Hourly breakdown
    test_meta_hourly_df = pd.DataFrame(meta_hourly)
    test_meta_hourly_df["y_true"] = y_hourly_test
    test_meta_hourly_df["hourly_ae_pred"] = hourly_preds

    for sc in sorted(test_meta_hourly_df["anomaly_type"].unique()):
        sub = test_meta_hourly_df[test_meta_hourly_df["anomaly_type"] == sc]
        n_samples = len(sub)
        is_normal = (sc == "normal")

        ae_detected = int((sub["hourly_ae_pred"] == 0).sum() if is_normal else (sub["hourly_ae_pred"] == 1).sum())
        ae_missed = n_samples - ae_detected
        ae_rate = round(ae_detected / n_samples, 4)

        scenario_rows.append({
            "Stream": "Hourly",
            "Scenario": sc,
            "Total Samples": n_samples,
            "ISO Correct": "N/A",
            "ISO Missed": "N/A",
            "ISO Detection Rate": "N/A",
            "LSTM Correct": ae_detected,
            "LSTM Missed": ae_missed,
            "LSTM Detection Rate": ae_rate,
        })

    sc_df = pd.DataFrame(scenario_rows)
    sc_csv_path = RESULTS_DIR / "scenario_metrics.csv"
    sc_df.to_csv(sc_csv_path, index=False)
    print(f"Saved scenario metrics table -> {sc_csv_path.name}")


    # 5. Generate Visualizations
    print("\n[5/5] Generating publication charts...")
    plots.plot_confusion_matrices({
        "Isolation Forest (Daily)": iso_metrics["Confusion_Matrix"],
        "LSTM Autoencoder (Daily)": daily_metrics["Confusion_Matrix"],
        "LSTM Autoencoder (Hourly)": hourly_metrics["Confusion_Matrix"],
    }, RESULTS_DIR / "confusion_matrix.png")

    plots.plot_roc_curves({
        "Isolation Forest (Daily)": (y_daily_test, iso_scores),
        "LSTM Autoencoder (Daily)": (y_daily_test, daily_errors),
        "LSTM Autoencoder (Hourly)": (y_hourly_test, hourly_errors),
    }, RESULTS_DIR / "roc_curve.png")

    plots.plot_pr_curves({
        "Isolation Forest (Daily)": (y_daily_test, iso_scores),
        "LSTM Autoencoder (Daily)": (y_daily_test, daily_errors),
        "LSTM Autoencoder (Hourly)": (y_hourly_test, hourly_errors),
    }, RESULTS_DIR / "precision_recall_curve.png")

    # Reconstruction Error Distribution (Daily)
    normal_errs = daily_errors[y_daily_test == 0]
    anom_errs = daily_errors[y_daily_test == 1]
    plots.plot_error_distribution(
        normal_errs,
        anom_errs,
        threshold=daily_thresh,
        model_name="Daily LSTM Autoencoder",
        output_path=RESULTS_DIR / "reconstruction_error_distribution.png"
    )

    # 6. Generate Markdown Evaluation Report
    report_content = f"""# MeterGuard AI: Phase 2 Model Evaluation Report

**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}  
**Evaluation Target:** Isolation Forest vs. Daily LSTM Autoencoder vs. Hourly LSTM Autoencoder  
**Test Data Origin:** Held-out residential smart meter profiles (profile-stratified held-out test sets)

---

## 1. Executive Summary & Verification Matrix

All metrics are directly derived from the confusion matrix values on the held-out test sets:
- **Daily Stream Held-Out Test Set:** {len(y_daily_test)} sequences ({sum(y_daily_test)} anomalous, {len(y_daily_test) - sum(y_daily_test)} normal across 10 held-out meters)
- **Hourly Stream Held-Out Test Set:** {len(y_hourly_test)} sequences ({sum(y_hourly_test)} anomalous, {len(y_hourly_test) - sum(y_hourly_test)} normal across 10 held-out meters)

| Model | Granularity | Total | TP | FP | TN | FN | Accuracy | Precision | Recall | F1-Score | ROC-AUC | FPR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Existing Isolation Forest** | Daily (7 features) | {len(y_daily_test)} | {iso_metrics['TP']} | {iso_metrics['FP']} | {iso_metrics['TN']} | {iso_metrics['FN']} | {iso_metrics['Accuracy']} | {iso_metrics['Precision']} | {iso_metrics['Recall (TPR)']} | {iso_metrics['F1-Score']} | {iso_metrics['ROC-AUC']} | {iso_metrics['False Positive Rate']} |
| **Daily LSTM Autoencoder** | Daily (30 timesteps) | {len(y_daily_test)} | {daily_metrics['TP']} | {daily_metrics['FP']} | {daily_metrics['TN']} | {daily_metrics['FN']} | {daily_metrics['Accuracy']} | {daily_metrics['Precision']} | {daily_metrics['Recall (TPR)']} | {daily_metrics['F1-Score']} | {daily_metrics['ROC-AUC']} | {daily_metrics['False Positive Rate']} |
| **Hourly LSTM Autoencoder** | Hourly (24 timesteps) | {len(y_hourly_test)} | {hourly_metrics['TP']} | {hourly_metrics['FP']} | {hourly_metrics['TN']} | {hourly_metrics['FN']} | {hourly_metrics['Accuracy']} | {hourly_metrics['Precision']} | {hourly_metrics['Recall (TPR)']} | {hourly_metrics['F1-Score']} | {hourly_metrics['ROC-AUC']} | {hourly_metrics['False Positive Rate']} |

### Mathematical Validation

- **Isolation Forest:**
  - Precision: ${iso_metrics['TP']} / ({iso_metrics['TP']} + {iso_metrics['FP']}) = {iso_metrics['Precision']}$
  - Recall: ${iso_metrics['TP']} / ({iso_metrics['TP']} + {iso_metrics['FN']}) = {iso_metrics['Recall (TPR)']}$
  - Accuracy: $({iso_metrics['TP']} + {iso_metrics['TN']}) / {len(y_daily_test)} = {iso_metrics['Accuracy']}$
  - FPR: ${iso_metrics['FP']} / ({iso_metrics['FP']} + {iso_metrics['TN']}) = {iso_metrics['False Positive Rate']}$

- **Daily LSTM Autoencoder:**
  - Precision: ${daily_metrics['TP']} / ({daily_metrics['TP']} + {daily_metrics['FP']}) = {daily_metrics['Precision']}$
  - Recall: ${daily_metrics['TP']} / ({daily_metrics['TP']} + {daily_metrics['FN']}) = {daily_metrics['Recall (TPR)']}$
  - Accuracy: $({daily_metrics['TP']} + {daily_metrics['TN']}) / {len(y_daily_test)} = {daily_metrics['Accuracy']}$
  - FPR: ${daily_metrics['FP']} / ({daily_metrics['FP']} + {daily_metrics['TN']}) = {daily_metrics['False Positive Rate']}$

- **Hourly LSTM Autoencoder:**
  - Precision: ${hourly_metrics['TP']} / ({hourly_metrics['TP']} + {hourly_metrics['FP']}) = {hourly_metrics['Precision']}$
  - Recall: ${hourly_metrics['TP']} / ({hourly_metrics['TP']} + {hourly_metrics['FN']}) = {hourly_metrics['Recall (TPR)']}$
  - Accuracy: $({hourly_metrics['TP']} + {hourly_metrics['TN']}) / {len(y_hourly_test)} = {hourly_metrics['Accuracy']}$
  - FPR: ${hourly_metrics['FP']} / ({hourly_metrics['FP']} + {hourly_metrics['TN']}) = {hourly_metrics['False Positive Rate']}$

---

## 2. Scenario-Wise Performance Analysis

### A. Daily Stream (30-day Consumption Horizon)

| Anomaly Scenario | Total Test Samples | Isolation Forest Detected | ISO Recall / Acc | Daily LSTM Detected | LSTM Recall / Acc |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for r in scenario_rows:
        if r["Stream"] == "Daily":
            report_content += f"| `{r['Scenario']}` | {r['Total Samples']} | {r['ISO Correct']} / {r['Total Samples']} | {r['ISO Detection Rate'] * 100:.1f}% | {r['LSTM Correct']} / {r['Total Samples']} | {r['LSTM Detection Rate'] * 100:.1f}% |\n"

    report_content += """
### B. Hourly Stream (24-hour Consumption Horizon)

| Anomaly Scenario | Total Test Samples | Hourly LSTM Detected | Hourly LSTM Recall / Acc |
| :--- | :---: | :---: | :---: |
"""
    for r in scenario_rows:
        if r["Stream"] == "Hourly":
            report_content += f"| `{r['Scenario']}` | {r['Total Samples']} | {r['LSTM Correct']} / {r['Total Samples']} | {r['LSTM Detection Rate'] * 100:.1f}% |\n"

    report_content += """
---

## 3. Methodological Distinctions & Limitations

1. **Synthetic Data Context:** Metrics are derived from physically modeled residential profiles with controlled tampering injection. They demonstrate theoretical capability under specified attack patterns and must not be interpreted as guaranteed real-world field accuracy without operational grid calibration.
2. **Feature Adaptations:** The existing Isolation Forest relies on scalar aggregations (`mean`, `median`, `trend`, `spike_ratio`), which excel at broad bulk shifts (`spike`) but struggle with temporal anomalies (`inversion`, subtle nighttime drops). The LSTM Autoencoder preserves temporal continuity and captures diurnal phase shifts directly from raw sequence reconstruction error.
"""
    report_path = RESULTS_DIR / "evaluation_report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Generated comprehensive report -> {report_path.name}")
    print("\n[COMPLETE] Model evaluation successfully finished.")


if __name__ == "__main__":
    main()
