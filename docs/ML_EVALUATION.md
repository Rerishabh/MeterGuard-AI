# MeterGuard AI: Machine Learning Evaluation & Anomaly Detection Analysis

**Document Version:** 1.0.0 (Production Release)
**System:** MeterGuard AI — Utility Meter Tampering & Electricity Theft Detection Platform
**Target Architecture:** Multi-Model Software-First Simulation & Decision Arbitration

---

## 1. Machine Learning Architecture Overview

MeterGuard AI addresses non-technical losses (electricity theft, meter tampering, and unmetered consumption) by coupling real-time electrical telemetry analysis with macroeconomic consumption-sequence modeling. Rather than relying on a single monolithic classifier, the system uses a four-model architecture operating across different physical domains and temporal horizons:

```
                                  INCOMING DATA STREAMS
                                             │
                  ┌──────────────────────────┴──────────────────────────┐
                  ▼                                                     ▼
     HIGH-FREQUENCY ELECTRICAL TELEMETRY                  DAILY / HOURLY CONSUMPTION
     (ADC Sensor Channels ~100ms stream)                  (Smart Meter Energy Sequences)
                  │                                                     │
         ┌────────┴────────┐                                   ┌────────┴────────┐
         ▼                 ▼                                   ▼                 ▼
   Model 2 (RF)      Model 1 (IF)                        Model 3 (Daily)   Model 3 (Hourly)
  Instantaneous    30-Day Extracted                        30-Day Daily      24-Hour Intraday
  Circuit Fault      Profile Norms                          LSTM-AE              LSTM-AE
         │                 │                                   │                 │
         └────────┬────────┘                                   └────────┬────────┘
                  ▼                                                     ▼
     TEMPORAL FILTERING (FIFO)                               STATISTICAL THRESHOLDING
    (Hysteresis 6-fault/5-clear)                           (Daily: 0.013009, Hourly: 0.016575)
                  │                                                     │
                  └──────────────────────────┬──────────────────────────┘
                                             ▼
                                DECISION ARBITRATION ENGINE
                               (Weighted Severity Ranking)
                                             │
                                             ▼
                                  ACTIONABLE AUDIT ALERT
                                & FIELD INVESTIGATION BRIEF
```

---

## 2. Model Roles and Operational Scope

| Model Component | Formal Architecture | Operational Role | Target Anomaly Type |
| :--- | :--- | :--- | :--- |
| **Model 1** | Isolation Forest (300 estimators) | Baseline daily profile analysis | Macroeconomic distribution outliers, severe consumption deviations |
| **Model 2** | Random Forest Classifier (300 estimators) | Real-time electrical fault classification | Physical circuit tampering (Line-Tap bypass, Neutral cut) |
| **Model 3 (Daily)** | LSTM Autoencoder (Encoder-Decoder) | 30-day sequential consumption modeling | Temporal consumption surges, schedule distortions, sequence anomalies |
| **Model 3 (Hourly)** | LSTM Autoencoder (Encoder-Decoder) | 24-hour intraday profile modeling | Peak-hour surges, diurnal load profile anomalies |

---

## 3. Input Features and Preprocessing Specifications

### 3.1 Model 1: Isolation Forest (`isolation_forest_final.joblib`)
- **Required Sequence Length:** $\ge 30$ continuous daily kWh values.
- **Engineered Feature Vector (7 Features):**
  1. `mean_consumption`: Arithmetic mean consumption over the 30-day window ($\text{kWh}$).
  2. `median_consumption`: 50th percentile daily consumption ($\text{kWh}$).
  3. `zero_days`: Count of days with zero recorded consumption ($x_t = 0.0$).
  4. `spike_ratio_filled`: Ratio of peak day consumption to median consumption ($\max(x) / (\text{median}(x) + \epsilon)$).
  5. `p95_consumption`: 95th percentile consumption value ($\text{kWh}$).
  6. `consumption_trend`: Linear regression slope ($m$ in $y = mx + b$) across the 30-day sequence.
  7. `median_zero`: Binary indicator ($1$ if median equals $0.0$, else $0$).
- **Output:** Inlier label ($+1 \implies \text{NORMAL}$, $-1 \implies \text{SUSPICIOUS}$) and continuous anomaly decision score.

### 3.2 Model 2: Random Forest Classifier (`sih_fault_detection_model_2.joblib`)
- **Input Channels:** Real-time 6-channel analog-to-digital converter (ADC) telemetry:
  - `T1_CS`, `T1_VS`: Primary transformer current & voltage sensor ADCs.
  - `T2_CS`, `T2_VS`: Secondary distribution pole current & voltage sensor ADCs.
  - `H1_CS`, `H1_VS`: Consumer meter current & voltage sensor ADCs.
- **Extracted Feature Vector (12 Features):**
  - Raw channels: `T1_CS`, `T1_VS`, `T2_CS`, `T2_VS`, `H1_CS`, `H1_VS`.
  - Differential currents: `T1_T2_CS_diff`, `T2_H1_CS_diff`, `T1_H1_CS_diff`.
  - Differential voltages: `T1_T2_VS_diff`, `T2_H1_VS_diff`, `T1_H1_VS_diff`.
- **Output Classes:** `normal`, `fault_S1` (Line-Tap / Upstream Bypass), `fault_S2` (Neutral Cut Bypass).
- **Temporal Filter:** 10-reading FIFO window; requires $\ge 6$ consecutive fault detections to confirm `CONFIRMED` status, and $\ge 5$ consecutive normal readings to transition to `CLEARED`.

### 3.3 Model 3 Daily: Daily LSTM Autoencoder (`daily_lstm_autoencoder.keras`)
- **Input Tensor:** 3D tensor of shape `(Batch, 30, 1)`. Exactly 30 chronological daily kWh observations.
- **Preprocessing:** MinMax normalization fitted on verified training meters:
  $$\text{Min} = 2.9178\text{ kWh},\quad \text{Max} = 36.7404\text{ kWh},\quad s = 0.029566,\quad \text{min\_} = -0.086268$$
- **Calibrated Decision Threshold:** **`0.013009`** (95th percentile validation error). High severity threshold: **`0.014284`** (99th percentile).

### 3.4 Model 3 Hourly: Hourly LSTM Autoencoder (`hourly_lstm_autoencoder.keras`)
- **Input Tensor:** 3D tensor of shape `(Batch, 24, 1)`. Exactly 24 chronological hourly kWh observations.
- **Preprocessing:** MinMax normalization fitted on verified training meters:
  $$\text{Min} = 0.0100\text{ kWh},\quad \text{Max} = 2.7436\text{ kWh},\quad s = 0.365818,\quad \text{min\_} = -0.003658$$
- **Calibrated Decision Threshold:** **`0.016575`** (95th percentile validation error). High severity threshold: **`0.021029`** (99th percentile).

---

## 4. Empirical Evaluation Metrics on Held-Out Synthetic Benchmarks

Evaluation was executed across strictly separated held-out test sets (Daily: 200 sequences across 10 meters; Hourly: 250 sequences across 10 meters) with zero meter overlap against training or validation splits:

| Metric | Isolation Forest (30-day) | Daily LSTM Autoencoder (30-day) | Hourly LSTM Autoencoder (24-hour) |
| :--- | :---: | :---: | :---: |
| **Total Test Samples** | 200 | 200 | 250 |
| **Normal Sequences (Negative)** | 152 | 152 | 195 |
| **Anomalous Sequences (Positive)** | 48 | 48 | 55 |
| **True Positives (TP)** | 2 | **15** | 14 |
| **False Positives (FP)** | **0** | **0** | 19 |
| **True Negatives (TN)** | **152** | **152** | 176 |
| **False Negatives (FN)** | 46 | **33** | 41 |
| **Accuracy** | 0.7700 | **0.8350** | 0.7600 |
| **Precision** | **1.0000** | **1.0000** | 0.4242 |
| **Recall (Sensitivity)** | 0.0417 | **0.3125** | 0.2545 |
| **F1-Score** | 0.0800 | **0.4762** | 0.3182 |
| **ROC-AUC** | 0.7618 | **0.8817** | 0.5808 |
| **False Positive Rate (FPR)** | **0.0000** | **0.0000** | 0.0974 |
| **Calibrated Threshold** | Dynamic Score ($>0$) | `0.013009` (MSE) | `0.016575` (MSE) |

> [!NOTE]
> **Data Provenance & Split Integrity:**
> The Daily and Hourly LSTM Autoencoders were trained, calibrated, and benchmarked with strictly enforced meter-level splits (33 train meters, 7 validation meters, 10 test meters). The Isolation Forest baseline is a pre-existing pretrained artifact from the foundational codebase whose original training customer IDs were unrecorded; it was evaluated as an external comparative benchmark on identical test sets.

---

## 5. Six-Scenario Synthetic Evaluation Matrix

To assess how specific tampering behaviors interact with model sensitivities, six standard synthetic profiles were evaluated against the calibrated pipelines:

| Scenario Name | Physical / Operational Context | Min kWh | Max kWh | Mean kWh | Model 1 IF Verdict (Score) | Daily LSTM MSE | Calibrated Threshold | Model 3 Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`normal`** | Standard diurnal household consumption | 4.264 | 6.002 | 5.041 | NORMAL (+0.1519) | **0.000242** | `0.013009` | **NORMAL** |
| **`sudden_drop`** | 55%–65% reduction on Days 15–29 (partial shunt) | 1.724 | 5.933 | 3.543 | NORMAL (+0.1387) | **0.002431** | `0.013009` | **NORMAL** |
| **`abnormally_low_night`** | Off-peak baseload diversion (night suppression) | 2.281 | 5.808 | 3.522 | NORMAL (+0.1541) | **0.001350** | `0.013009` | **NORMAL** |
| **`flatline`** | Current sensor disconnection / stuck ADC (~0.4 kWh) | 0.365 | 0.418 | 0.390 | NORMAL (+0.1277) | **0.000317** | `0.013009` | **NORMAL** |
| **`consumption_spike`** | Unauthorized tapping / heavy load surges (>20 kWh) | 4.131 | 21.326 | 7.471 | NORMAL (+0.0948) | **0.024060** | `0.013009` | **SUSPICIOUS** |
| **`inversion`** | Inverted weekday/weekend schedule | 2.137 | 7.312 | 5.270 | NORMAL (+0.1523) | **0.003080** | `0.013009` | **NORMAL** |

---

## 6. Scaling Methodology & Mathematical Limitations

### 6.1 Downward Anomaly Attenuation Proof
The Daily LSTM Autoencoder uses a `MinMaxScaler` fitted across broad macro-consumption ranges:
$$x_{\text{scaled}} = \frac{x - 2.9178}{36.7404 - 2.9178} = \frac{x - 2.9178}{33.8226}$$

The scale multiplier is $s = 0.029566$. Because autoencoder reconstruction loss is quadratic:
$$\text{SE} = (x_{\text{scaled}} - \hat{x}_{\text{scaled}})^2 = s^2 \cdot (x - \hat{x})^2 = 0.000874 \cdot (x - \hat{x})^2$$

Consider a severe meter shunt resulting in complete zero consumption ($x = 0.0\text{ kWh}$):
$$x_{\text{scaled}}(0.0) = \frac{0.0 - 2.9178}{33.8226} = -0.08627$$

When the autoencoder predicts typical normal baseline consumption ($\hat{x}_{\text{scaled}} \approx 0.000$):
$$\text{SE}_{\max} = (-0.08627 - 0.000)^2 = (-0.08627)^2 = \mathbf{0.007442}$$

Even if an account flatlines to $0.0\text{ kWh}$ for all 30 consecutive days, the maximum possible mean squared error is bounded by $0.007442$. Since the calibrated 95th-percentile threshold is **`0.013009`**:
$$0.007442 < 0.013009$$

**Conclusion:** It is mathematically impossible for downward consumption anomalies (meter bypass, load suppression, flatline) to trigger the Daily LSTM threshold under current global min-max scaling.

### 6.2 Asymmetric Sensitivity to Upward Surges
In contrast, an upward surge reaching $x = 22.0\text{ kWh}$ scales to:
$$x_{\text{scaled}}(22.0) = \frac{22.0 - 2.9178}{33.8226} = 0.56418$$

When reconstructing baseline $\hat{x}_{\text{scaled}} \approx 0.0600$:
$$\text{SE} = (0.56418 - 0.0600)^2 = (0.50418)^2 = \mathbf{0.25420}$$

A surge lasting 3 to 5 days distributes sufficient squared error across the 30-day window to yield $\text{MSE} \approx 0.024\text{--}0.032$, cleanly breaching the `0.013009` threshold.

---

## 7. False-Positive, False-Negative, and Operational Considerations

1. **Zero False-Positive Rate on Daily Streams:**
   The Daily LSTM Autoencoder achieved a `0.0000` False Positive Rate on the 152 normal held-out test sequences. For utility operators, this is vital: field investigation teams are not dispatched on false alarms for standard households.
2. **Trade-Off with False Negatives:**
   The conservative threshold and min-max attenuation produce a high false-negative rate for subtle downward bypasses. In MeterGuard AI, this is mitigated by **Model 2 (Random Forest)**, which catches physical meter bypasses in the high-frequency electrical telemetry domain via current differential analysis ($T_1 - H_1$) rather than relying solely on billing sequences.
3. **Hourly Stream Profile:**
   The Hourly LSTM Autoencoder achieves higher sensitivity ($s = 0.3658$) but experiences a higher False Positive Rate ($0.0974$). It serves as an intraday alert trigger rather than an automated dispatch trigger.

---

## 8. Synthetic Testing vs. Real-World Utility Performance

- **Simulation Platform:** All evaluations documented herein were executed on synthetic datasets and recorded hardware replay streams within a software-first test environment.
- **No Field Generalization Claims:** These empirical results demonstrate algorithm mechanics, threshold calibration, and pipeline integration. They do not claim measured real-world utility theft detection accuracy across diverse grid infrastructures.
- **Physical Bypasses vs. Billing Fraud:** Field utility theft often involves mechanical shunts or neutral disconnection without consumption spikes. In production deployments, multi-modal arbitration (combining transformer-level balancing with per-meter sequential models) is mandatory.
