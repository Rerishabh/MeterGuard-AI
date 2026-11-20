# MeterGuard AI: Machine Learning & Time-Series Anomaly Detection

This directory contains the time-series anomaly detection pipeline for **MeterGuard AI: Utility Meter Tampering Detector**.

The pipeline uses **LSTM Autoencoders** trained on normal consumption sequences to detect subtle and temporal electricity tampering patterns that conventional statistical and shallow tree models (such as Isolation Forest) fail to capture.

---

## 1. Architecture Overview

An Autoencoder learns to reconstruct normal time-series sequences. When exposed to an anomalous sequence (e.g. meter bypass, sudden drop, or load inversion), the reconstruction error (Mean Squared Error) spikes significantly above an empirical threshold.

```text
Input Sequence [Batch, Timesteps, 1]
       │
       ▼
LSTM Encoder (32 units, ReLU)  ──>  Latent Vector [Batch, 16]
       │
       ▼
RepeatVector (Timesteps)
       │
       ▼
LSTM Decoder (32 units, ReLU)
       │
       ▼
TimeDistributed Dense(1, Linear) ──> Reconstructed Sequence [Batch, Timesteps, 1]
```

### Models Implemented

1. **Daily Stream (30-day Horizon):**
   - **Artifact:** `ml/artifacts/daily_lstm_autoencoder.keras`
   - **Sequence Length:** 30 timesteps
   - **Features:** Daily kWh consumption
   - **Active Threshold (95th percentile):** `0.008470` (MSE)
   - **99th Percentile Threshold:** `0.009379` (MSE)

2. **Hourly Stream (24-hour Horizon):**
   - **Artifact:** `ml/artifacts/hourly_lstm_autoencoder.keras`
   - **Sequence Length:** 24 timesteps
   - **Features:** Hourly kWh consumption
   - **Active Threshold (95th percentile):** `0.013904` (MSE)
   - **99th Percentile Threshold:** `0.017935` (MSE)

---

## 2. Dataset Preparation & Preprocessing

### Synthetic Consumption Streams

To benchmark detection against realistic tampering scenarios, `ml/dataset/generate_synthetic_data.py` generates two datasets:

- **`synthetic_daily_consumption.csv`:** 30,000 readings across 1,000 sequences of 30 days (816 normal, 184 anomalous).
- **`synthetic_hourly_consumption.csv`:** 30,000 readings across 1,250 sequences of 24 hours (1,020 normal, 230 anomalous).

### Modeled Tampering Scenarios

1. **Sudden Drop:** Drop in consumption by 50% to 85% mid-sequence (simulates partial physical meter bypass).
2. **Abnormally Low Night:** Depressed baseline during nighttime hours (simulates off-peak theft).
3. **Flatline:** Constant low readings with zero natural variance (simulates disconnected or bypassed current coil).
4. **Consumption Spike:** Extreme unnatural surges (simulates unauthorized tapping or meter malfunction).
5. **Inversion:** Reverse correlation or negative consumption offset (simulates reverse current injection or phase inversion).

### Leakage-Free Data Splitting

- Splitting is performed **strictly by `meter_id`** (70% train, 15% validation, 15% held-out test).
- The Autoencoder is trained **exclusively on normal sequences** from the training set.
- Scalers (`MinMaxScaler` wrapped in `SequenceScaler`) are fitted strictly on normal training data and serialized to `daily_scaler.pkl` and `hourly_scaler.pkl`.

---

## 3. Training & Threshold Calibration

Training is implemented in `ml/training/train_lstm_ae.py` using:
- **Optimizer:** Adam ($lr = 0.001$)
- **Loss:** Mean Squared Error (MSE)
- **Batch Size:** 32
- **Epochs:** 30 with EarlyStopping (patience 5)

Thresholds are calculated by taking the reconstruction MSE on the normal validation split:
- **`threshold_95`:** 95th percentile of validation reconstruction error.
- **`threshold_99`:** 99th percentile of validation reconstruction error.

Saved metadata is stored in `ml/artifacts/daily_threshold.json` and `ml/artifacts/hourly_threshold.json`.

---

## 4. Benchmark Results: LSTM-AE vs. Isolation Forest

Evaluation is performed in `ml/evaluation/evaluate_models.py` on held-out test sets (Daily: 200 sequences across 10 meters; Hourly: 250 sequences across 10 meters).

> [!IMPORTANT]
> **Data Provenance & Split Integrity Distinction:**
> - **Daily and Hourly LSTM Autoencoders** were trained, calibrated, and evaluated with **verified meter-level separation** (33 training meters, 7 validation meters, 10 held-out test meters; 0 overlap across all sets).
> - **Existing Isolation Forest (`models/isolation_forest_final.joblib`)** is a pre-existing pretrained baseline from the initial codebase. Because its original training script and training customer IDs are unavailable in the repository, its historical training-data separation cannot be verified. It is evaluated here as a comparative pretrained baseline using the 7 engineered features on the 200 synthetic 30-day test sequences.

### Model Comparison Table

| Metric | Isolation Forest (30-day) | Daily LSTM-AE (30-day) | Hourly LSTM-AE (24-hour) |
| :--- | :---: | :---: | :---: |
| **Total Test Samples** | 200 | 200 | 250 |
| **True Positives (TP)** | 2 | **15** | 14 |
| **False Positives (FP)** | 0 | 0 | 19 |
| **True Negatives (TN)** | 152 | 152 | 176 |
| **False Negatives (FN)** | 46 | **33** | 41 |
| **Accuracy** | `0.7700` | **`0.8350`** | `0.7600` |
| **Precision** | `1.0000` | `1.0000` | `0.4242` |
| **Recall (TPR)** | `0.0417` | **`0.3125`** | `0.2545` |
| **F1-Score** | `0.0800` | **`0.4762`** | `0.3182` |
| **ROC-AUC** | `0.7618` | **`0.8817`** | `0.5808` |
| **False Positive Rate** | `0.0000` | `0.0000` | `0.0974` |
| **Threshold** | Dynamic Decision Score | `0.013009` (MSE) | `0.016575` (MSE) |

### Scenario Breakdown

#### Daily Stream (30-day Horizon):
| Scenario | Samples | Isolation Forest Detection | Daily LSTM-AE Detection |
| :--- | :---: | :---: | :---: |
| **Consumption Spike** | 9 | 1 / 9 (11.1%) | **7 / 9 (77.8%)** |
| **Flatline** | 8 | 1 / 8 (12.5%) | **2 / 8 (25.0%)** |
| **Inversion** | 8 | 0 / 8 (0.0%) | **1 / 8 (12.5%)** |
| **Sudden Drop** | 9 | 0 / 9 (0.0%) | **2 / 9 (22.2%)** |
| **Abnormally Low Night** | 14 | 0 / 14 (0.0%) | **3 / 14 (21.4%)** |
| **Normal Baseline** | 152 | 152 / 152 (100.0%) | 152 / 152 (100.0%) |

#### Hourly Stream (24-hour Horizon):
| Scenario | Samples | Hourly LSTM-AE Detection |
| :--- | :---: | :---: |
| **Consumption Spike** | 11 | **6 / 11 (54.5%)** |
| **Abnormally Low Night** | 10 | **3 / 10 (30.0%)** |
| **Inversion** | 14 | **3 / 14 (21.4%)** |
| **Sudden Drop** | 10 | **2 / 10 (20.0%)** |
| **Flatline** | 10 | 0 / 10 (0.0%) |
| **Normal Baseline** | 195 | 176 / 195 (90.3%) |

Visual evaluation plots are available in `ml/evaluation/results/`:
- `roc_curve.png`
- `precision_recall_curve.png`
- `confusion_matrix.png`
- `reconstruction_error_distribution.png`
- `evaluation_report.md`

---

## 5. Flask Inference Integration & Architectural Separation

### A. Architectural Separation of Hardware Telemetry vs. Consumption Sequences

- **`POST /api/meter-data`:** Dedicated to high-frequency hardware sensor telemetry (~100ms intervals from ESP32). It executes electrical calculations, the Random Forest hardware fault model, and the Isolation Forest prototype model. High-frequency sensor samples are **not** fed into daily or hourly consumption Autoencoders. If no consumption sequence has been analyzed for the meter, the LSTM block reports `AWAITING SUFFICIENT HISTORY`.
- **`POST /api/anomaly/analyze`:** Dedicated consumption-based sequence analysis endpoint. Accepts valid 30-day (Daily) or 24-hour (Hourly) non-negative kWh observations.

### B. Input Validation Protocol

The endpoint enforces strict physical and mathematical validation (rejecting invalid requests with HTTP 400):
- **Meter ID:** Non-empty string.
- **Sequence Type:** `"daily"` or `"hourly"` (case-insensitive).
- **Sequence Length:** Exactly 30 values for daily; exactly 24 values for hourly.
- **Numeric Integrity:** Strictly numeric floats/integers (no strings, booleans, or None).
- **Finiteness:** `NaN` and `Infinity` are rejected.
- **Non-Negativity:** Negative consumption values ($v < 0$ kWh) are rejected as physically invalid.

### C. Example Valid Request & Response

```http
POST /api/anomaly/analyze
Content-Type: application/json

{
  "meter_id": "M001",
  "sequence_type": "daily",
  "consumption": [
    5.1, 4.8, 5.3, 5.0, 4.9, 5.2, 5.4, 5.1, 4.7, 5.0,
    5.3, 5.1, 4.8, 5.2, 5.0, 5.4, 5.1, 4.9, 5.2, 5.0,
    5.3, 5.1, 4.8, 5.2, 5.0, 5.4, 5.1, 4.9, 5.2, 5.0
  ]
}
```

Response (HTTP 200):
```json
{
  "is_anomaly": false,
  "meter_id": "M001",
  "reconstruction_error": 0.000038,
  "sequence_length": 30,
  "sequence_type": "daily",
  "status": "NORMAL",
  "threshold": 0.00847,
  "threshold_99": 0.009379,
  "timestamp": "2026-11-16T01:27:27.718480"
}
```


---

## 6. How to Reproduce

Run the following commands from the project root:

```powershell
# 1. Generate synthetic consumption streams
python ml/dataset/generate_synthetic_data.py --samples 1000

# 2. Train Daily and Hourly LSTM Autoencoders
python ml/training/train_lstm_ae.py --epochs 30 --batch-size 32

# 3. Benchmark models and generate evaluation report & plots
python ml/evaluation/evaluate_models.py

# 4. Run backend endpoint test
python backend/test_decision_logic.py
```
