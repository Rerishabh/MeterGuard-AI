# MeterGuard AI: Utility Meter Tampering Detector

MeterGuard AI is an intelligent monitoring and decision-support system designed to detect electricity theft, utility meter tampering, and abnormal consumption behaviors using high-frequency smart meter telemetry, physics-based transformer differentials, and machine learning models.

---

## 1. Problem Statement

Non-Technical Losses (NTL) such as direct line tapping, meter tampering, and neutral bypass cost global electrical utilities tens of billions of dollars annually while destabilizing distribution grids. Conventional fraud detection relies heavily on periodic manual audits or simplistic threshold rules, resulting in high false-positive rates and delayed detection. MeterGuard AI addresses this challenge by cross-referencing household consumption profiles with upstream transformer and pole-level sensor differentials to detect and localize physical and statistical tampering in real time.

---

## 2. Project Objectives

- **Dual-Model Inference:** Combine long-term consumption pattern analysis with real-time transformer-to-meter electrical differentials.
- **Hysteresis Temporal Filtering:** Prevent transient spikes and sensor noise from triggering false alarms through sliding-window alert confirmation.
- **Automated Severity Triage:** Categorize meter conditions into actionable priorities (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Hardware-in-the-Loop & Simulated Replay:** Ingest live readings from microcontrollers (e.g., ESP32 testbeds) or replay recorded hardware test datasets for testing and demonstrations.
- **Operator Dashboard:** Provide utility dispatchers with interactive GIS maps, live power line charts, and meter network health metrics.

---

## 3. Technology Stack

### Backend
- **Framework:** Python 3.10+ / FastAPI 0.115+ (Primary) and Flask 3.1.2 (Fallback)
- **Data & Numerical Processing:** NumPy, Pandas, Pydantic 2.x, Pydantic Settings
- **Machine Learning & Inference:** scikit-learn, Joblib, TensorFlow 2.x / Keras 3
- **ORM & Persistence (Phase 3A):** SQLAlchemy 2.x, PyMySQL, Cryptography
- **Database Migrations (Phase 3A):** Alembic 1.13+
- **Database Engine:** MySQL 8.0 / MariaDB (relational persistence for meters, readings, sequences, alerts, and forensic reports)
- **Future Architecture (Phase 3B):** Gemini 2.5 Flash / Google GenAI SDK for automated field investigation reports


### Frontend
- **Framework:** React 19 + Vite 8
- **Visualizations:** Recharts (Line Charts & Bar Charts)
- **Geographic Mapping:** Leaflet & React-Leaflet (OpenStreetMap)
- **Icons & Styling:** Lucide React, Custom CSS Variables

---

## 4. Implemented Machine Learning Models

MeterGuard AI utilizes a multi-model approach:

1. **Model 1: Consumption Pattern Anomaly Detector (`models/isolation_forest_final.joblib`)**
   - **Algorithm:** Isolation Forest (`contamination=0.08`, `n_estimators=300`)
   - **Provenance:** Existing pretrained baseline from legacy repository (unverified historical training provenance; external benchmark feature formulation).
   - **Input:** 7 statistical features derived from household consumption history: `mean_consumption`, `median_consumption`, `zero_days`, `spike_ratio_filled`, `p95_consumption`, `consumption_trend`, and `median_zero`.
   - **Output:** Identifies long-term consumption anomalies (`NORMAL` vs. `SUSPICIOUS`).
2. **Model 2: Hardware Differential Fault Classifier (`models/sih_fault_detection_model_2.joblib`)**
   - **Algorithm:** Random Forest Classifier (`n_estimators=300`)
   - **Input:** 12 electrical features combining raw sensor measurements and pairwise current/voltage differentials across Transformer 1 ($T_1$), Pole $T_2$, and House $H_1$.
   - **Output:** Classifies physical tampering states: `normal`, `fault_S1` (bypass), or `fault_S2` (line tap).
3. **Model 3: Time-Series Anomaly Detector (`ml/artifacts/daily_lstm_autoencoder.keras`, `ml/artifacts/hourly_lstm_autoencoder.keras`)**
   - **Algorithm:** Deep LSTM Autoencoder (Encoder-Decoder architecture)
   - **Provenance:** Trained and validated with verified meter-level separation (33 train meters, 7 val meters, 10 held-out test meters; 0 overlap).
   - **Input:** Raw sequential consumption profiles (Daily 30-day or Hourly 24-hour sequence).
   - **Output:** Sequence reconstruction Mean Squared Error (MSE) compared against dynamic 95th/99th percentile validation thresholds. Outperforms Isolation Forest on temporal patterns (ROC-AUC `0.8817` vs `0.7618`).



### Decision Arbitration Matrix

Predictions from both models pass through a temporal sliding-window filter (10 readings, requiring 6 positive detections to confirm and 5 consecutive normals to clear) into `backend/decision_logic.py`:

| Model 1 Result | Model 2 Result | Final Status | Priority | Action |
| :--- | :--- | :--- | :--- | :--- |
| `SUSPICIOUS` | `FAULT_S1` / `FAULT_S2` | **HIGH PRIORITY ALERT** | `CRITICAL` | Immediate field inspection |
| `NORMAL` / `WAITING` | `FAULT_S1` / `FAULT_S2` | **FAULT DETECTED** | `HIGH` | Physical tampering investigation |
| `SUSPICIOUS` | `NORMAL` | **SUSPICIOUS** | `MEDIUM` | Flag for consumption monitoring |
| `NORMAL` | `NORMAL` | **NORMAL** | `LOW` | Normal operation |
| `WAITING` | `NORMAL` | **MONITORING** | `LOW` | Baseline data collection |

---

## 5. Hardware Dataset Description

The repository includes real testbed telemetry in `data/hardware_dataset.csv`:
- **Dimensions:** 899 rows $\times$ 8 columns (39.7 KB)
- **Sensors:** `time_ms`, `T1_CS`, `T1_VS`, `T2_CS`, `T2_VS`, `H1_CS`, `H1_VS`, `label`
- **Sampling Interval:** ~100 ms (~30 seconds continuous test bench recording)
- **Class Distribution:**
  - `fault_S1`: 300 readings (33.4%)
  - `fault_S2`: 300 readings (33.4%)
  - `normal`: 299 readings (33.3%)
- **Origin:** Recorded from an ESP32 hardware test rig connected to current transformers and calibrated voltage sensors under normal and staged tamper switch states ($S_1$, $S_2$).

---

## 6. Project Directory Structure

```text
elctricity-theft-prediction-ml-main/
├── .env.example                               # Environment configuration template
├── .gitignore                                 # Git ignore specification
├── README.md                                  # Comprehensive documentation
├── requirements.txt                           # Backend dependencies (Flask, FastAPI, ML, SQLAlchemy)
├── assets/                                    # Static media assets
├── backend/
│   ├── alembic.ini                            # Alembic migration configuration
│   ├── app.py                                 # Flask fallback application server
│   ├── main.py                                # FastAPI root runner entry point
│   ├── decision_logic.py                      # Rule-based status arbitration matrix
│   ├── model1_features.py                     # 7-feature engineering for consumption profile
│   ├── model2_features.py                     # 12-feature engineering for electrical differentials
│   ├── replay_hardware_dataset.py            # Hardware dataset replay simulator
│   ├── test_backend_suite.py                  # Flask regression test suite
│   ├── test_fastapi_phase3a.py                # FastAPI & persistence verification suite
│   ├── alembic/                               # Alembic migration environment
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py          # Initial schema for 5 core tables
│   ├── app/                                   # Modular FastAPI application package
│   │   ├── __init__.py
│   │   ├── main.py                            # FastAPI application with CORS & lifespan
│   │   ├── config.py                          # Pydantic Settings configuration loader
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── db_models.py                   # SQLAlchemy ORM models (5 tables)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py                      # GET / and GET /api/health
│   │   │   ├── telemetry.py                   # POST /api/meter-data
│   │   │   ├── anomaly.py                     # POST /api/anomaly/analyze
│   │   │   └── dashboard.py                   # GET /api/dashboard, /meters, /alerts
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── telemetry.py                   # Pydantic telemetry input schemas
│   │   │   ├── anomaly.py                     # Pydantic sequence validation schemas
│   │   │   ├── meter.py                       # Pydantic meter location schemas
│   │   │   ├── alert.py                       # Pydantic alert schemas
│   │   │   └── dashboard.py                   # Pydantic dashboard response schemas
│   │   └── services/
│   │       ├── __init__.py
│   │       └── ml_engine.py                   # Unified ML inference & state engine
│   └── database/                              # SQLAlchemy database infrastructure
│       ├── __init__.py
│       ├── base.py                            # Declarative Base metadata
│       └── session.py                         # Engine, SessionLocal, get_db, health check
├── data/
│   └── hardware_dataset.csv                   # 899 rows of ESP32 sensor telemetry
├── frontend/
│   ├── index.html                             # Web application entry HTML
│   ├── package.json                           # React 19 dependencies & scripts
│   ├── vite.config.js                         # Vite bundling configuration
│   ├── public/                                # Public web assets
│   └── src/
│       ├── App.css                            # Dashboard styling & layout definitions
│       ├── App.jsx                            # Root React component
│       ├── index.css                          # Minimal base reset
│       ├── main.jsx                           # Application DOM mount
│       ├── components/
│       │   ├── MeterSummaryCard.jsx           # Electrical metrics & status card
│       │   ├── NetworkDifferentialCard.jsx    # T1/T2/H1 sensor differential inspection
│       │   └── Sidebar.jsx                    # Navigation and branding sidebar
│       ├── charts/
│       │   ├── LiveElectricalChart.jsx        # Real-time power line chart
│       │   └── LoadProfileChart.jsx           # 30-day consumption bar chart
│       ├── pages/
│       │   └── DashboardPage.jsx              # Main operations dashboard view
│       └── services/
│           └── api.js                         # Centralized frontend API service
├── ml/                                        # ML experimentation, models & artifacts
│   ├── artifacts/
│   │   ├── daily_lstm_autoencoder.keras
│   │   ├── hourly_lstm_autoencoder.keras
│   │   ├── daily_scaler.pkl
│   │   ├── hourly_scaler.pkl
│   │   ├── daily_threshold.json
│   │   └── hourly_threshold.json
│   ├── dataset/
│   │   ├── generate_synthetic_data.py
│   │   ├── synthetic_daily_consumption.csv
│   │   └── synthetic_hourly_consumption.csv
│   ├── evaluation/
│   │   ├── evaluate_models.py
│   │   └── results/
│   ├── preprocessing/
│   └── training/
└── models/
    ├── isolation_forest_final.joblib          # Pretrained Isolation Forest
    └── sih_fault_detection_model_2.joblib     # Pretrained Random Forest Classifier
```

---

## 7. Installation & Startup Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ and npm 9+ (tested on Node 24 / npm 11)
- MySQL Server 8.0+ / MariaDB (Windows service: `MySQL80`)

### A. Environment & Database Configuration

1. Copy the environment configuration template:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Configure your MySQL credentials inside `.env`:
   ```env
   DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/meterguard_db
   API_HOST=0.0.0.0
   API_PORT=5000
   MODEL1_PATH=models/isolation_forest_final.joblib
   MODEL2_PATH=models/sih_fault_detection_model_2.joblib
   ML_ARTIFACTS_DIR=ml/artifacts
   VITE_API_BASE_URL=http://localhost:5000
   ```
3. Install Python dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Verify MySQL service and create the database:
   ```powershell
   # Check Windows MySQL service status
   Get-Service *mysql*
   
   # Log in to MySQL CLI and create the database
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS meterguard_db;"
   ```
5. Apply Alembic database migrations:
   ```powershell
   python -m alembic -c backend/alembic.ini upgrade head
   ```

### B. Starting the Backend Server

#### Primary FastAPI Server (Phase 3A):
```powershell
# Option 1: Root entry script
python backend/main.py

# Option 2: Direct Uvicorn invocation
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 5000
```
FastAPI runs on `http://127.0.0.1:5000` with interactive Swagger docs at `http://127.0.0.1:5000/docs`.

#### Fallback Flask Server:
The legacy Flask backend remains completely available as a preserved fallback:
```powershell
python backend/app.py
```

### C. Frontend Setup

1. Open a second terminal and navigate to `frontend/`:
   ```powershell
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```powershell
   npm run dev
   ```
3. Open your browser at `http://localhost:5173`.

---

## 8. Hardware Telemetry Replay Simulator

To stream telemetry to the backend without a physical ESP32 connected, run the built-in dataset replay tool:

```powershell
# Continuous looping replay (recommended for dashboard demos)
python backend/replay_hardware_dataset.py --delay 1.0 --loop

# Run a single pass with custom delay
python backend/replay_hardware_dataset.py --delay 0.5 --repeat 1

# Send telemetry for a specific meter ID
python backend/replay_hardware_dataset.py --meter-id M001 --delay 1.0 --loop
```

The simulator reads `data/hardware_dataset.csv`, maps sensor columns to the API schema, and posts readings sequentially to `POST /api/meter-data`, printing live model predictions in the console.

---

## 9. API Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /` | `GET` | Service status and health banner |
| `GET /api/health` | `GET` | Health status, loaded model indicators, database connection flag, active meter count |
| `POST /api/meter-data` | `POST` | Ingests sensor readings, executes Models 1 & 2, runs temporal filter, persists reading, deduplicates alerts |
| `POST /api/anomaly/analyze` | `POST` | Ingests daily (30-step) or hourly (24-step) consumption sequences, evaluates LSTM Autoencoder anomaly score, persists sequence |
| `GET /api/dashboard` | `GET` | Aggregated telemetry, live readings history, and alert statuses for all meters |
| `GET /api/meters` | `GET` | List of registered meters, connection states, and geographic coordinates |
| `GET /api/meter/<meter_id>` | `GET` | Detailed telemetry and history for a specific meter |
| `GET /api/alerts` | `GET` | Audit trail of anomaly alerts from MySQL with optional filtering (`meter_id`, `severity`, `limit`) |
| `POST /api/reports/generate` | `POST` | Generates a grounded forensic investigation report using Gemini 2.5 Flash or deterministic fallback, and persists to MySQL |
| `GET /api/reports/<meter_id>` | `GET` | Retrieves all forensic investigation reports for a specific meter (newest first) |
| `GET /api/reports` | `GET` | Retrieves recent forensic investigation reports across all meters |
| `POST /api/simulate/tamper` | `POST` | Executes one of 6 realistic 30-day consumption scenarios, evaluates Daily LSTM, persists sequence, updates alerts, and optionally auto-generates report |

---

## 10. Phase 3B: Gemini Forensic Reports & Tampering Simulator

### Architecture & Grounded GenAI
Phase 3B introduces an evidence-grounded Generative AI investigation layer using the official **Google GenAI Python SDK (`google-genai`)** and **Gemini 2.5 Flash (`gemini-2.5-flash`)**.
- **Role Boundary:** Machine learning models (Isolation Forest, Random Forest, Daily & Hourly LSTM Autoencoders) make 100% of detection decisions. Gemini **never** overrides ML predictions, invents measurements, or confirms theft without physical audit.
- **Deterministic Evidence Fallback:** If `GEMINI_API_KEY` is absent, invalid, or reaches quota, the system seamlessly uses a deterministic Markdown engine based on exact stored telemetry, setting `model_used="deterministic-fallback"`.
- **Structured 5-Section Reports:**
  1. Executive Summary (Meter, severity, detection model, simulated vs. live badge, primary finding).
  2. Observed Consumption & Sensor Evidence (Reconstruction MSE vs. threshold, statistics, differentials).
  3. Technical Root-Cause Hypotheses (Partial bypass, magnetic interference, night-load diversion, sensor drift).
  4. Prioritized Field Inspection Checklist (Actionable checkboxes for utility crews).
  5. Recommended Next Steps (Dispatch protocol, telemetry polling, archival).

### Tampering Simulator Scenarios
The simulator (`backend/app/services/tamper_simulator.py`) generates realistic 30-day daily consumption profiles with physical bounds ($>0$ kWh):
1. `normal`: Clean baseline (~5.0 kWh/day with natural variance).
2. `sudden_drop`: Abrupt 55–65% reduction in the second half of the month.
3. `abnormally_low_night`: Systematic basal suppression / nighttime diversion.
4. `flatline`: Constant stuck/shunt reading (~0.4 kWh/day).
5. `consumption_spike`: Severe intermittent surges exceeding 14.0 kWh/day.
6. `inversion`: Inverted weekday/weekend profile (suppressed weekend, elevated weekday).

---

## 11. Complete Windows PowerShell Demo Instructions

### Terminal 1: Start FastAPI Primary Backend
```powershell
uvicorn backend.app.main:app --host 0.0.0.0 --port 5000 --reload
```
*API docs available at `http://localhost:5000/docs`*

### Terminal 2: Start React Frontend
```powershell
cd frontend
npm run dev
```
*Dashboard opens at `http://localhost:5173`*

### Terminal 3: Stream Live Hardware Telemetry Replay
```powershell
python backend/replay_hardware_dataset.py --delay 1.0 --loop
```

### Terminal 4: Run Tampering Simulation or Generate Reports via CLI
```powershell
# Simulate consumption spike on M001 and auto-generate forensic report
Invoke-RestMethod -Method POST -Uri "http://localhost:5000/api/simulate/tamper" -ContentType "application/json" -Body '{"meter_id":"M001","scenario":"consumption_spike","auto_generate_report":true}'

# Fetch generated reports for M001
Invoke-RestMethod -Method GET -Uri "http://localhost:5000/api/reports/M001"
```

---

## 12. Current Implementation Status

### Verified & Implemented (Phase 1, Phase 2, Phase 3A & Phase 3B)
- [x] Modular FastAPI architecture (`backend/app/`) with Pydantic configuration, schemas, and routes.
- [x] Flask backend (`backend/app.py`) preserved completely untouched as the operational fallback.
- [x] SQLAlchemy ORM layer (`backend/database/` and `backend/app/models/db_models.py`) with 5 relational models (`meters`, `hardware_readings`, `consumption_sequences`, `anomaly_alerts`, `investigation_reports`).
- [x] Alembic migration pipeline (`001_initial_schema.py` and `002_add_scenario.py`) applied to MySQL 8.0.
- [x] Unified ML Engine (`backend/app/services/ml_engine.py`) preserving all four models, feature engineering, calibrations, temporal filters, and arbitration logic.
- [x] Strict time-resolution separation (100ms hardware telemetry vs. 30-day/24-hour consumption profiles).
- [x] Resilient database connectivity handling: API remains alive with graceful degradation when database is offline.
- [x] Alert deduplication preventing duplicate database alerts during continuous active tampering.
- [x] Official Google GenAI SDK (`google-genai`) integration with Gemini 2.5 Flash and robust deterministic fallback engine.
- [x] One-Click Tampering Simulator with 6 realistic 30-day scenarios and honest Daily LSTM Autoencoder evaluation.
- [x] React 19 Frontend Investigation Dashboard:
  - Interactive Tampering Simulator Card with Recharts 30-day line graph and threshold reference line.
  - Forensic Investigation Brief Panel with Markdown preview, history selector, `.md` report download, and interactive inspection checklist.
- [x] Complete automated test suites:
  - Phase 3B suite (`backend/test_phase3b.py`): 7/7 suites PASS (100%).
  - Phase 3A regression (`backend/test_fastapi_phase3a.py`): 6/6 suites PASS (100%).
  - Flask fallback regression (`backend/test_backend_suite.py`): 5/5 suites PASS (100%).
  - Frontend ESLint: 0 errors, 0 warnings.
  - Frontend Production Build: Vite production bundle built cleanly in 1.70s.

