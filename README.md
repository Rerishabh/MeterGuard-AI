# MeterGuard AI: Utility Meter Tampering Detector

**MeterGuard AI** is an intelligent, software-first monitoring and decision-support platform engineered to detect electricity theft, utility meter tampering, and non-technical distribution losses. By synthesizing high-frequency electrical telemetry replay, macroeconomic consumption pattern analysis, and deep recurrent autoencoders, the platform identifies fraudulent accounts and prioritizes targeted field investigations across utility service territories.

---

## 1. Original Problem Statement

> *"Utilities want to catch meter tampering and billing anomalies indicating energy theft, but manual field checks across large service areas don't scale. A system learning normal usage-pattern behavior via autoencoder and flagging deviations would prioritize accounts for field investigation."*

Electricity theft and non-technical losses (NTL) cost global electric utilities tens of billions of dollars annually, destabilize local distribution networks, and create serious public safety hazards. Conventional utility fraud detection relies on delayed billing audits or rigid manual inspection schedules that fail to catch sophisticated tampering. MeterGuard AI addresses this challenge with automated, multi-model anomaly detection and intelligent triage.

---

## 2. Project Objectives

- **Multi-Horizon Tamper Detection:** Combine instantaneous physical electrical circuit fault detection with multi-week consumption sequence anomaly detection.
- **Hysteresis Temporal Filtering:** Apply rolling-window confirmation buffers to eliminate false alarms caused by transient electrical noise and intermittent grid fluctuations.
- **Actionable Account Triage:** Automatically rank utility accounts into an **Account Investigation Priority Queue** (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) to optimize field investigation dispatch.
- **Software-First Simulation:** Provide a reproducible, full-fidelity simulation environment powered by recorded hardware datasets and synthetic scenario injection without requiring physical electrical test rigs.
- **Auditable Alert Lifecycle:** Maintain an immutable, deduplicated historical incident log with model-isolated auto-resolution.

---

## 3. Software-First Simulation Architecture

MeterGuard AI is designed as a **software-first simulation and evaluation platform**.

> [!IMPORTANT]
> **No Physical Hardware Required:**
> The application does **NOT** require physical electricity meters, physical ESP32/microcontroller testbeds, physical GPS receivers, or live electrical connections.

The platform simulates realistic utility operations through two decoupled streaming mechanisms:
1. **Automated Hardware Dataset Replay:** When the FastAPI backend starts, a dedicated background simulation worker streams real-world testbed telemetry from recorded datasets (`data/hardware_dataset.csv`), simulating real-time electrical sensor feeds across distribution transformers and meters.
2. **Synthetic Anomaly Injection:** Operators can inject calibrated 30-day consumption profiles across six realistic tampering scenarios (`normal`, `sudden_drop`, `abnormally_low_night`, `flatline`, `consumption_spike`, `inversion`) to benchmark detection models on demand.

### End-to-End Operational Workflow

```
Normal Electrical Consumption
             │
             ▼
 High-Frequency Stream Replay & Sequence Evaluation
             │
             ▼
 Anomaly & Tamper Detection (Random Forest + LSTM Autoencoders)
             │
             ▼
 Suspicious Meter Identification & Priority Queue Ranking
             │
             ▼
 Deduplicated Alert Generation & MySQL Audit Logging
             │
             ▼
 Forensic Investigation Brief & Field Inspection Recommendation
```

---

## 4. Machine Learning Detection Models

MeterGuard AI deploys four complementary machine learning models to monitor distinct physical and temporal characteristics:

```
                            METERGUARD AI MODEL SUITE
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           ▼                                                         ▼
PHYSICAL ELECTRICAL CIRCUIT                               CONSUMPTION PROFILE SEQUENCE
           │                                                         │
   Model 2: Random Forest                                    Model 1: Isolation Forest
   - 300 decision trees                                      - 300 estimators, SGCC baseline
   - 12 raw & differential ADC features                      - 7 statistical summary features
   - Detects Line-Tap & Neutral Cut                          - Macroeconomic distribution outlier
           │                                                         │
           ▼                                                         ▼
  Instantaneous Hardware Fault                             Model 3: LSTM Autoencoders
  Classification (~100ms stream)                           - Daily 30-day stream (0.013009 threshold)
                                                           - Hourly 24-hour stream (0.016575 threshold)
                                                           - Deep recurrent sequence reconstruction
```

### Model Specifications

| Model Identifier | Architecture | Input Data | Target Tampering Behavior | Calibrated Threshold |
| :--- | :--- | :--- | :--- | :---: |
| **Model 1** | Isolation Forest (Scikit-Learn) | 7 engineered statistical features from 30-day history | Macroeconomic consumption outliers | Dynamic Score ($>0 \implies \text{Normal}$) |
| **Model 2** | Random Forest Classifier | 6 ADC sensor channels + 6 differential features | Instantaneous circuit bypass (Line-Tap $S_1$, Neutral Cut $S_2$) | 6/10 FIFO Confirmation Window |
| **Model 3 (Daily)** | Deep LSTM Autoencoder (Keras) | 30 continuous daily $\text{kWh}$ values | Multi-day energy diversion, surge anomalies | **`0.013009`** MSE (95th percentile) |
| **Model 3 (Hourly)** | Deep LSTM Autoencoder (Keras) | 24 continuous hourly $\text{kWh}$ values | Intraday peak surges, off-peak diversion | **`0.016575`** MSE (95th percentile) |

For comprehensive mathematical proofs, scaling limits, and six-scenario benchmark results, see [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md).

---

## 5. Decision Arbitration & Priority Queue

Predictions from physical telemetry and sequential consumption are reconciled through a centralized arbitration engine (`backend/decision_logic.py`):

| Model 1 (IF) | Model 2 (RF) | Model 3 (Daily LSTM) | Final Status | Priority | Operational Field Action |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `SUSPICIOUS` | `FAULT_S1` / `FAULT_S2` | `SUSPICIOUS` | **CRITICAL FAULT** | `CRITICAL` | Immediate emergency dispatch; confirmed bypass & diversion |
| `NORMAL` / `WAITING` | `FAULT_S1` / `FAULT_S2` | Any | **FAULT DETECTED** | `HIGH` | Physical meter inspection; hardware circuit imbalance |
| Any | `NORMAL` | `SUSPICIOUS` | **SUSPICIOUS** | `MEDIUM` | Billing audit; meter calibration & load inspection |
| `NORMAL` | `NORMAL` | `NORMAL` | **NORMAL** | `LOW` | Account healthy; standard continuous monitoring |
| `WAITING` | `NORMAL` | `WAITING` | **MONITORING** | `LOW` | Account initializing; accumulating history |

---

## 6. Technology Stack

### Backend
- **Framework:** FastAPI 0.115+ (Asynchronous Python 3.10+)
- **ORM & Database:** SQLAlchemy 2.x, Alembic, MySQL 8.0+
- **Machine Learning:** TensorFlow 2.x / Keras 3, Scikit-Learn 1.9+, Joblib, NumPy, Pandas
- **Validation & Settings:** Pydantic 2.x, Pydantic-Settings

### Frontend
- **Framework:** React 19 + Vite 8
- **UI Architecture:** Responsive 4-section layout with slide-in Settings drawer
- **Visualizations:** Recharts (high-frequency electrical load curves, 30-day bar charts)
- **Styling & Icons:** Modular CSS with design system variables, Lucide React

---

## 7. Directory Structure

```text
elctricity-theft-prediction-ml-main/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint & lifespan manager
│   │   ├── config.py                   # Pydantic environment configuration
│   │   ├── models/db_models.py         # SQLAlchemy relational database models
│   │   ├── routes/                     # Modular API routers
│   │   │   ├── health.py               # Health & ML readiness probes
│   │   │   ├── telemetry.py            # High-frequency telemetry ingestion & RF filter
│   │   │   ├── anomaly.py              # Sequence analysis & LSTM inference
│   │   │   ├── dashboard.py            # Operational priority queue & meter status
│   │   │   ├── reports.py              # Tampering simulation & report generation
│   │   │   └── simulation.py           # Background simulation manager controls
│   │   └── services/                   # ML engine, simulation service, report generator
│   ├── database/                       # Database engine & session factories
│   ├── decision_logic.py               # Multi-model decision arbitration matrix
│   ├── test_alert_lifecycle.py         # 10-point alert lifecycle regression test
│   └── test_backend_suite.py           # Comprehensive backend verification suite
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     # Root application container & slide-in drawer
│   │   ├── pages/                      # Four core application views
│   │   │   ├── DashboardPage.jsx       # Account priority queue & meter network
│   │   │   ├── AiDetectionPage.jsx     # Multi-model evaluation cards & simulator
│   │   │   ├── LiveMonitoringPage.jsx  # High-frequency electrical telemetry curves
│   │   │   ├── AlertsLogsPage.jsx      # Deduplicated audit log & incident history
│   │   │   └── SettingsPage.jsx        # Database health & simulation controls (Drawer)
│   │   └── services/api.js             # Frontend API client
│   └── package.json                    # Frontend dependencies & build scripts
├── data/
│   └── hardware_dataset.csv            # Authentic 899-row recorded testbed telemetry
├── docs/
│   └── ML_EVALUATION.md                # Comprehensive ML metrics & mathematical analysis
├── models/                             # Pretrained tree model binaries (.joblib)
├── ml/                                 # LSTM training pipelines, scalers, and artifacts
├── assets/
│   └── screenshots/                    # Verified application interface captures
├── .env.example                        # Safe environment template
├── requirements.txt                    # Python dependency manifest
└── README.md                           # Primary project documentation
```

---

## 8. Installation & Setup

### Prerequisites
- **Python:** 3.10, 3.11, or 3.12
- **Node.js:** v18.0.0 or higher (v20+ recommended)
- **MySQL Server:** 8.0 or MariaDB 10.5+

### Step 1: Clone Repository & Configure Environment
```bash
git clone https://github.com/Rerishabh/MeterGuard-AI.git
cd MeterGuard-AI

# Create local environment file from template
copy .env.example .env     # Windows
# cp .env.example .env     # Linux / macOS
```

Review `.env` and verify database credentials:
```ini
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/meterguard_ai
API_HOST=127.0.0.1
API_PORT=5000
VITE_API_URL=http://localhost:5000
```

### Step 2: Set Up MySQL Database
Create the target database in MySQL:
```sql
CREATE DATABASE IF NOT EXISTS meterguard_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Apply database migrations:
```bash
# In your Python environment:
alembic upgrade head
```

### Step 3: Backend Python Environment
```bash
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\activate       # Windows PowerShell
# source .venv/bin/activate    # Linux / macOS

pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Frontend Node Environment
```bash
cd frontend
npm install
cd ..
```

---

## 9. Running the Application

### 1. Start the FastAPI Backend
```bash
# From the project root with .venv active:
python -m uvicorn backend.app.main:app --port 5000 --reload
```
- **Backend API:** `http://localhost:5000`
- **Interactive OpenAPI Documentation:** `http://localhost:5000/docs`
- Upon startup, the background simulation worker begins streaming `data/hardware_dataset.csv` automatically.

### 2. Start the React Frontend
```bash
# In a separate terminal:
cd frontend
npm run dev
```
- **Web Interface:** `http://localhost:5173`

---

## 10. Frontend Navigation & User Interface

The application interface is organized into **four primary sections**, with system settings accessible via a persistent slide-in drawer:

1. **Dashboard:** Displays overall system operational status, meter network summary metrics, and the real-time **Account Investigation Priority Queue** ranking accounts by urgency.
2. **AI Detection:** Detailed diagnostic breakdown of all four models (Isolation Forest, Random Forest, Daily LSTM, Hourly LSTM) and the interactive **Tampering Simulator** card.
3. **Live Telemetry:** High-frequency, real-time electrical line charts displaying Transformer 1 ($T_1$), Pole Transformer ($T_2$), and Consumer ($H_1$) current, voltage, and power curves.
4. **Alerts & Logs:** Searchable, auditable incident log displaying active and resolved tamper alerts with model isolation, full taxonomy labels (`SIMULATED_...`, `FAULT_...`), and timestamps.
5. **Settings (Slide-in Drawer):** Opened via the sidebar footer gear icon (`⚙`); provides live MySQL connectivity diagnostics, polling frequency controls, and background simulation management.

---

## 11. Core REST API Endpoints

| Method | Endpoint | Description | Sample Parameters / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service and ML model readiness probe | None |
| `GET` | `/api/dashboard` | Aggregated operations status & priority queue | None |
| `GET` | `/api/meter/{meter_id}` | Detailed telemetry and model states for a meter | Path: `meter_id` (`M001`, `M002`) |
| `POST` | `/api/meter-data` | Ingests high-frequency electrical telemetry frame | `{"meter_id": "M001", "T1_CS": 3000, ...}` |
| `POST` | `/api/evaluate-sequence` | Evaluates 30-day daily or 24-hr hourly sequence | `{"meter_id": "M001", "sequence_type": "daily", "consumption": [...]}` |
| `POST` | `/api/simulate/tamper` | Injects synthetic 30-day tampering scenario | `{"meter_id": "M001", "scenario": "consumption_spike"}` |
| `GET` | `/api/alerts` | Queries audited historical anomaly alerts | Query: `meter_id`, `severity`, `limit` |
| `GET` | `/api/simulation/status`| Queries active dataset replay worker status | None |

---

## 12. Application Screenshots

### Dashboard
![MeterGuard AI Dashboard](assets/screenshots/dashboard.png)

### AI Detection
![AI Detection](assets/screenshots/ai-detection.png)

### Live Simulation
![Live Simulation](assets/screenshots/live-simulation.png)

### Alerts and Logs
![Alerts and Logs](assets/screenshots/alerts-and-logs.png)

> [!NOTE]
> *The screenshots directory `assets/screenshots/` contains clean interface captures representing the final 4-section architecture.*

---

## 13. Testing & Verification

MeterGuard AI includes automated test suites covering backend API contracts, ML inference, and alert lifecycle mechanics:

### 1. Alert Lifecycle & Model Isolation Suite
Verifies the 10-point alert lifecycle, guaranteeing Random Forest telemetry clears only RF alerts, sequence evaluations deduplicate properly, and scenario simulations remain isolated:
```bash
python backend/test_alert_lifecycle.py
```

### 2. Complete Backend Verification Suite
Validates health probes, daily and hourly sequence inference, and all 10 edge-case input rejections (NaN, negative values, malformed sequences):
```bash
python backend/test_backend_suite.py
```

### 3. Frontend Code Quality & Production Build
```bash
# ESLint check (0 errors, 0 warnings)
npm --prefix frontend run lint

# Production Vite build
npm --prefix frontend run build
```

---

## 14. Known Limitations & Technical Context

1. **Software-First Simulation:** The platform operates strictly in a simulated environment using recorded testbench datasets and synthetic profiles. It does not interface with physical AMI smart meters or field grid SCADA systems.
2. **MinMaxScaler Attenuation on Low Consumption:** As detailed in [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md), the Daily LSTM Autoencoder's global min-max scaling ($[2.92, 36.74]\text{ kWh}$) quadratically attenuates downward errors. Complete meter flatlines achieve a maximum theoretical MSE of $0.007442$, which does not cross the calibrated $0.013009$ threshold. Physical shunts are instead detected via **Model 2 (Random Forest)** electrical current differentials.
3. **Synthetic Anomaly Scope:** Synthetic scenario evaluations demonstrate algorithmic behavior and threshold mechanics under controlled profiles; they do not represent statistical field performance across millions of customer accounts.

---

## 15. License

This project is developed for educational, academic, and research evaluation purposes under the MIT License.
