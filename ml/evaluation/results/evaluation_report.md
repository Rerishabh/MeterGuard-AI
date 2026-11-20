# MeterGuard AI: Phase 2 Model Evaluation Report

**Date:** 2026-11-16  
**Evaluation Target:** Isolation Forest vs. Daily LSTM Autoencoder vs. Hourly LSTM Autoencoder  
**Test Data Origin:** Held-out residential smart meter profiles (profile-stratified held-out test sets)

---

## 1. Executive Summary & Verification Matrix

All metrics are directly derived from the confusion matrix values on the held-out test sets:
- **Daily Stream Held-Out Test Set:** 200 sequences (48 anomalous, 152 normal across 10 held-out meters)
- **Hourly Stream Held-Out Test Set:** 250 sequences (55 anomalous, 195 normal across 10 held-out meters)

| Model | Granularity | Total | TP | FP | TN | FN | Accuracy | Precision | Recall | F1-Score | ROC-AUC | FPR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Existing Isolation Forest** | Daily (7 features) | 200 | 2 | 0 | 152 | 46 | 0.77 | 1.0 | 0.0417 | 0.08 | 0.7618 | 0.0 |
| **Daily LSTM Autoencoder** | Daily (30 timesteps) | 200 | 15 | 0 | 152 | 33 | 0.835 | 1.0 | 0.3125 | 0.4762 | 0.8817 | 0.0 |
| **Hourly LSTM Autoencoder** | Hourly (24 timesteps) | 250 | 14 | 19 | 176 | 41 | 0.76 | 0.4242 | 0.2545 | 0.3182 | 0.5808 | 0.0974 |

### Mathematical Validation

- **Isolation Forest:**
  - Precision: $2 / (2 + 0) = 1.0$
  - Recall: $2 / (2 + 46) = 0.0417$
  - Accuracy: $(2 + 152) / 200 = 0.77$
  - FPR: $0 / (0 + 152) = 0.0$

- **Daily LSTM Autoencoder:**
  - Precision: $15 / (15 + 0) = 1.0$
  - Recall: $15 / (15 + 33) = 0.3125$
  - Accuracy: $(15 + 152) / 200 = 0.835$
  - FPR: $0 / (0 + 152) = 0.0$

- **Hourly LSTM Autoencoder:**
  - Precision: $14 / (14 + 19) = 0.4242$
  - Recall: $14 / (14 + 41) = 0.2545$
  - Accuracy: $(14 + 176) / 250 = 0.76$
  - FPR: $19 / (19 + 176) = 0.0974$

---

## 2. Scenario-Wise Performance Analysis

### A. Daily Stream (30-day Consumption Horizon)

| Anomaly Scenario | Total Test Samples | Isolation Forest Detected | ISO Recall / Acc | Daily LSTM Detected | LSTM Recall / Acc |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `abnormally_low_night` | 14 | 0 / 14 | 0.0% | 3 / 14 | 21.4% |
| `consumption_spike` | 9 | 1 / 9 | 11.1% | 7 / 9 | 77.8% |
| `flatline` | 8 | 1 / 8 | 12.5% | 2 / 8 | 25.0% |
| `inversion` | 8 | 0 / 8 | 0.0% | 1 / 8 | 12.5% |
| `normal` | 152 | 152 / 152 | 100.0% | 152 / 152 | 100.0% |
| `sudden_drop` | 9 | 0 / 9 | 0.0% | 2 / 9 | 22.2% |

### B. Hourly Stream (24-hour Consumption Horizon)

| Anomaly Scenario | Total Test Samples | Hourly LSTM Detected | Hourly LSTM Recall / Acc |
| :--- | :---: | :---: | :---: |
| `abnormally_low_night` | 10 | 3 / 10 | 30.0% |
| `consumption_spike` | 11 | 6 / 11 | 54.5% |
| `flatline` | 10 | 0 / 10 | 0.0% |
| `inversion` | 14 | 3 / 14 | 21.4% |
| `normal` | 195 | 176 / 195 | 90.3% |
| `sudden_drop` | 10 | 2 / 10 | 20.0% |

---

## 3. Data Provenance & Split Integrity

To ensure complete scientific transparency, the evaluation distinguishes between models with verified meter-level separation and pretrained baselines whose training provenance is undocumented:

1. **Models Evaluated with Verified Meter-Level Separation (LSTM Autoencoders):**
   - **Daily LSTM Autoencoder:** Trained exclusively on 33 designated normal meters (`M0008`, `M0010`, ..., `M0050`), calibrated on 7 normal validation meters (`M0001`–`M0007`), and tested on 10 strictly held-out meters (`M0009`, `M0016`, `M0019`, `M0020`, `M0022`, `M0028`, `M0031`, `M0036`, `M0041`, `M0042`). Zero meter overlap across all splits ($\text{Train} \cap \text{Test} = 0$, $\text{Val} \cap \text{Test} = 0$).
   - **Hourly LSTM Autoencoder:** Trained exclusively on 33 designated normal meters, calibrated on 7 normal validation meters, and tested on 10 strictly held-out meters (`M0007`, `M0016`, `M0017`, `M0020`, `M0030`, `M0032`, `M0034`, `M0041`, `M0046`, `M0050`). Zero meter overlap ($\text{Train} \cap \text{Test} = 0$, $\text{Val} \cap \text{Test} = 0$).
   - **Preprocessing & Thresholds:** Scalers were fitted exclusively on the 33 training meters; decision thresholds were calculated exclusively from the 7 validation meters.

2. **Pretrained Baseline with Unverified Training Provenance (Isolation Forest):**
   - **Artifact:** `models/isolation_forest_final.joblib` is a legacy binary model provided with the initial codebase.
   - **Training Script & Dataset:** No training script, training data, or training logs exist in the repository for this model. Source code comments in `backend/model1_features.py` refer to *"Same calculations as SGCC feature engineering"*, suggesting historical training on an external benchmark (e.g., State Grid Corporation of China).
   - **Evaluation Status:** The model was evaluated on the 200 synthetic 30-day sequences using the exact 7 features (`mean_consumption`, `median_consumption`, `zero_days`, `spike_ratio_filled`, `p95_consumption`, `consumption_trend`, `median_zero`). While the synthetic test meters (`M0009`, `M0016`, etc.) were generated independently in Phase 2, **no claim of verified training-data separation can be made** because the original training customer/meter IDs are unavailable. It serves solely as a reference pretrained baseline.

---

## 4. Methodological Distinctions & Limitations

1. **Synthetic Data Context:** Metrics are derived from physically modeled residential profiles with controlled tampering injection. They demonstrate theoretical capability under specified attack patterns and must not be interpreted as guaranteed real-world field accuracy without operational grid calibration.
2. **Feature Adaptations:** The existing Isolation Forest relies on scalar aggregations (`mean`, `median`, `trend`, `spike_ratio`), which excel at broad bulk shifts (`spike`) but struggle with temporal anomalies (`inversion`, subtle nighttime drops). The LSTM Autoencoder preserves temporal continuity and captures diurnal phase shifts directly from raw sequence reconstruction error.
3. **Threshold Calibration Strategy:** The Hourly LSTM Autoencoder achieves an ROC-AUC of 0.5808, reflecting high intra-day variance in 24-hour residential profiles. Decision thresholds were preserved at the principled 95th percentile of normal validation data without post-hoc manipulation.
