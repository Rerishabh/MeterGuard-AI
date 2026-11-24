# MeterGuard AI: Utility Meter Tampering Detector

> **An intelligent, multi-model anomaly detection and field investigation decision-support platform engineered to detect electricity theft, utility meter tampering, and non-technical distribution losses.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Vite 8](https://img.shields.io/badge/Vite-8.0-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![MySQL 8.0](https://img.shields.io/badge/MySQL-8.0%2B-4479A1.svg?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![TensorFlow / Keras](https://img.shields.io/badge/TensorFlow%20%2F%20Keras-2.x%20%2F%203.x-FF6F00.svg?logo=tensorflow&logoColor=white)](https://tensorflow.org/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.9%2B-F7931E.svg?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-red.svg)](https://alembic.sqlalchemy.org/)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [Software-First Simulation Architecture](#3-software-first-simulation-architecture)
4. [Machine Learning Detection Models](#4-machine-learning-detection-models)
5. [Decision Arbitration & Priority Queue](#5-decision-arbitration--priority-queue)
6. [Technology Stack](#6-technology-stack)
7. [System Architecture & Repository Structure](#7-system-architecture--repository-structure)
8. [Installation & Local Setup](#8-installation--local-setup)
9. [Running the Application Locally](#9-running-the-application-locally)
10. [Core REST API Endpoints](#10-core-rest-api-endpoints)
11. [Testing & Verification](#11-testing--verification)
12. [Known Limitations & Technical Context](#12-known-limitations--technical-context)

---

## 1. Project Overview

Electricity theft and non-technical losses (NTL) cost global electric utilities over $96 billion annually, destabilizing local distribution grids, creating severe public safety hazards, and imposing unrecoverable financial burdens on power distribution companies. Traditional utility fraud detection relies on delayed monthly billing reconciliations or random manual field audits across vast geographical territories -- methods that do not scale and fail to capture sophisticated, intermittent physical bypasses.

**MeterGuard AI** is a software-first monitoring and decision-support platform designed to automate tampering detection and optimize utility field inspection workflows. By coupling real-time electrical telemetry replay with deep recurrent sequence reconstruction, the platform identifies fraudulent accounts and automatically ranks them into an **Account Investigation Priority Queue** (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), replacing blind physical checks with targeted, intelligence-driven dispatch.

---

## 2. Key Features

- **Dual-Path Inference Engine:** Decouples high-frequency electrical circuit monitoring from long-horizon consumption sequence modeling.
- **Live Electrical Telemetry Visualization:** Interactive waveform charts displaying Phase Current, Neutral Current, Voltage, and Power readings across simulated distribution nodes.
- **Deep Sequence Reconstruction:** Daily (30-day) and hourly (24-hour) LSTM Autoencoders to detect unmetered consumption, schedule distortion, and night diversion.
- **Interactive Tampering Simulator:** Test and demonstrate six calibrated tampering profiles (`normal`, `sudden_drop`, `abnormally_low_night`, `flatline`, `consumption_spike`, `inversion`) with live reconstruction error plotting.
- **AI-Powered Forensic Investigation Briefs:** Automatic synthesis of meter telemetry and anomaly history into structured field inspection briefs via Google Gemini GenAI.
- **Centralized Operational Dashboard:** Real-time summary metrics, meter registry table, and prioritized investigation queue.
- **Settings Slide-in Drawer:** Dedicated control panel for database health checks, live polling frequency adjustments, and background simulation management.

---

## 3. Software-First Simulation Architecture

MeterGuard AI is architected from the ground up as a **software-first simulation platform**.

> [!IMPORTANT]
> **No Physical Hardware Required:**
> The application does **NOT** require physical electricity meters, physical ESP32 or microcontroller testbenches, physical current transformers, GPS receivers, or live electrical connections.

The simulation platform operates via two independent mechanisms:

1. **Automated Hardware Dataset Replay:** When the FastAPI backend initializes, a dedicated background replay worker streams recorded electrical sensor data from `data/hardware_dataset.csv`. This dataset contains 899 authentic records sampled at 100ms intervals from an ESP32 ADC sensor testbench across staged tamper states:
   - `normal` (299 records): Balanced load, normal neutral return.
   - `fault_S1` (300 records): Line-Tap / phase bypass (current diverted around the measurement shunt).
   - `fault_S2` (300 records): Neutral Cut / earth return diversion (neutral disconnected, return current grounded).
2. **Synthetic Anomaly Injection:** Operators can inject calibrated 30-day consumption profiles across six realistic tampering scenarios (`normal`, `sudden_drop`, `abnormally_low_night`, `flatline`, `consumption_spike`, `inversion`) to benchmark detection models on demand via the UI or REST API.

---

## 4. Machine Learning Detection Models

MeterGuard AI deploys four complementary machine learning models to monitor distinct physical and temporal characteristics:

| Model Identifier | Architecture | Input Data | Target Tampering Behavior | Calibrated Threshold |
| :--- | :--- | :--- | :--- | :---: |
| **Model 1** | Isolation Forest (Scikit-Learn) | 7 engineered statistical features from 30-day history | Statistical consumption-pattern outlier | Dynamic Score ($>0 \implies \text{Normal}$) |
| **Model 2** | Random Forest Classifier | 6 ADC sensor channels + 6 differential features | Instantaneous circuit bypass (Line-Tap $S_1$, Neutral Cut $S_2$) | 6/10 FIFO Confirmation Window |
| **Model 3 (Daily)** | Deep LSTM Autoencoder (Keras) | 30 continuous daily $\text{kWh}$ values | Multi-day energy diversion, surge anomalies | **`0.013009`** MSE (95th percentile) |
| **Model 3 (Hourly)** | Deep LSTM Autoencoder (Keras) | 24 continuous hourly $\text{kWh}$ values | Intraday peak surges, off-peak diversion | **`0.016575`** MSE (95th percentile) |

### Important: Two Separate Inference Paths

The system strictly decouples its inference execution into two operational paths. The four models **do not** run concurrently on every incoming telemetry frame:

1. **Real-Time Telemetry Inference Path:**
   - Evaluates incoming electrical sensor readings against **Model 2 (Random Forest)** and incorporates historical baseline metrics from **Model 1 (Isolation Forest)**.
   - Predictions pass through a 10-reading rolling FIFO window for temporal smoothing before confirming an electrical fault.
2. **On-Demand Consumption Sequence Inference Path:**
   - Evaluates 30-day daily or 24-hour hourly energy sequences using **Model 3 (Daily LSTM)** or **Model 4 (Hourly LSTM)**.
   - Calculates reconstruction Mean Squared Error (MSE) and compares against calibrated anomaly thresholds. Triggered on demand during batch analysis or tampering simulation.

For detailed mathematical proofs, feature formulas, and benchmark results, see [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md).

---

## 5. Decision Arbitration & Priority Queue

Predictions from physical telemetry and sequential consumption are reconciled through a centralized arbitration engine (`backend/decision_logic.py`):

| Priority | Final Status | Model States (M1 / M2 / M3) | Operational Field Action |
| :---: | :--- | :--- | :--- |
| **CRITICAL** | High Priority Alert | IF Suspicious + RF Fault (`FAULT_S1` / `FAULT_S2`) + LSTM Suspicious | Immediate emergency dispatch; confirmed bypass & diversion |
| **HIGH** | Fault Detected | RF Fault (`FAULT_S1` / `FAULT_S2`) | Physical meter inspection; hardware circuit imbalance |
| **MEDIUM** | Suspicious | Daily LSTM Anomaly or IF Baseline Outlier | Billing audit; meter calibration & load inspection |
| **LOW** | Normal / Monitoring | All Models Normal or Accumulating Baseline History | Account healthy; standard continuous monitoring |

### Hysteresis Temporal Filtering
To prevent transient voltage dips, electrical switching noise, and sensor fluctuations from triggering false alarms, raw predictions from Model 2 enter a rolling 10-reading FIFO buffer:
- **Fault Confirmation:** A fault is confirmed only when at least **6 out of the last 10 readings** indicate a fault state (`FAULT_S1` or `FAULT_S2`).
- **Fault Clearing:** A confirmed fault is resolved only when **5 consecutive readings** are evaluated as `NORMAL`.

### Alert Identity & Model Isolation
Alerts are identified by the composite key `(meter_id, source_model, fault_type)`:
- **Deduplication:** Subsequent anomaly readings update the existing active incident rather than creating duplicate rows.
- **Model Isolation:** Normal electrical telemetry resolves *only* Random Forest alerts. Normal sequence evaluation resolves *only* sequence alerts. Normal simulation resolves *only* simulated alerts. An active physical bypass alert is never cleared by an unrelated consumption sequence check.

---

## 6. Technology Stack

| Category | Component | Technology / Library | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend** | API Framework | FastAPI 0.115+ | High-performance asynchronous REST API server |
| | Data Validation | Pydantic v2 & Pydantic-Settings | Request schema validation and environment loading |
| | ORM & Migrations | SQLAlchemy 2.0 & Alembic | Database modeling and schema version control |
| | Web Server | Uvicorn | ASGI production server |
| **Machine Learning** | Tree Models | Scikit-Learn 1.9+ & Joblib | Isolation Forest (M1) and Random Forest (M2) |
| | Deep Learning | TensorFlow 2.x / Keras 3 | Daily and Hourly LSTM Autoencoders (M3/M4) |
| | Data Processing | NumPy & Pandas | Array manipulation and feature scaling |
| **Database** | Primary Store | MySQL 8.0+ / MariaDB 10.5+ | Persistent storage for telemetry, meters, and audit logs |
| | Database Driver | PyMySQL | Pure-Python MySQL client for SQLAlchemy |
| **Frontend** | UI Framework | React 19 | Component-based interactive user interface |
| | Build Tool | Vite 8 | Fast development server and optimized bundle build |
| | Data Visualization | Recharts | Real-time waveform curves and load profile charts |
| | Icons & Styling | Lucide React & Modular CSS | Clean utility theme with CSS design tokens |
| **GenAI** | Field Briefs | Google Gemini API (gemini-2.5-flash) | Structured forensic investigation reports |

---

## 7. System Architecture & Repository Structure

### Data Flow Architecture

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Background Telemetry        │       │   Synthetic Scenario Injection  │
│    (hardware_dataset.csv)       │       │    (6 Tampering Profiles)       │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 ▼                                         ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend                                 │
│                                                                           │
│   ┌─────────────────────────┐             ┌───────────────────────────┐   │
│   │ Telemetry Router        │             │ Anomaly & Report Routers  │   │
│   │ POST /api/meter-data    │             │ POST /api/evaluate-seq    │   │
│   └────────────┬────────────┘             └─────────────┬─────────────┘   │
│                │                                        │                 │
│                ▼                                        ▼                 │
│   ┌─────────────────────────┐             ┌───────────────────────────┐   │
│   │ Model 2 (Random Forest) │             │ Models 3 & 4 (LSTM-AE)    │   │
│   │ FIFO Window (6/10)      │             │ Reconstruction Error Eval │   │
│   └────────────┬────────────┘             └─────────────┬─────────────┘   │
│                │                                        │                 │
│                └───────────────────┬────────────────────┘                 │
│                                    │                                      │
│                                    ▼                                      │
│                     ┌─────────────────────────────┐                       │
│                     │ Decision Arbitration Engine │                       │
│                     │  (backend/decision_logic.py)│                       │
│                     └──────────────┬──────────────┘                       │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
      ┌───────────────────────────┐     ┌───────────────────────────┐
      │     MySQL Database        │     │     React 19 Frontend     │
      │  - meters                 │     │  - Priority Queue UI      │
      │  - telemetry              │     │  - Waveform Load Curves   │
      │  - anomaly_alerts         │     │  - Anomaly Diagnostics    │
      │  - investigation_reports  │     │  - Settings Drawer        │
      └───────────────────────────┘     └───────────────────────────┘
```

### Repository Structure

```text
elctricity-theft-prediction-ml-main/
├── backend/                  # FastAPI application, routers, services & Alembic migrations
│   ├── alembic/              # Database migration version scripts
│   ├── alembic.ini           # Alembic migration configuration
│   └── app/                  # Application core, API routes, database models, and ML engine
├── frontend/                 # React 19 + Vite dashboard application
│   ├── src/                  # Application components, pages, charts, and API client
│   └── package.json          # Frontend dependencies and npm scripts
├── data/                     # Hardware dataset (899-row recorded testbed telemetry)
├── docs/                     # Technical documentation & ML evaluation analysis
├── models/                   # Pretrained tree model binaries (.joblib)
├── ml/                       # LSTM models, scalers, and training artifacts
├── .env.example              # Environment configuration template
└── requirements.txt          # Python dependency manifest
```

---

## 8. Installation & Local Setup

### Prerequisites
- **Python:** 3.10, 3.11, or 3.12 (64-bit)
- **Node.js:** v18.0.0 or higher (v20+ LTS recommended)
- **MySQL Server:** 8.0 or MariaDB 10.5+ running locally on port 3306
- **Windows PowerShell** or standard bash shell

### Step 1: Clone Repository
```powershell
git clone https://github.com/Rerishabh/MeterGuard-AI.git
cd MeterGuard-AI
```

### Step 2: Configure Environment
Copy the template configuration to `.env`:
```powershell
copy .env.example .env
```

Edit `.env` to verify your local MySQL database credentials:
```ini
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/meterguard_ai
API_HOST=127.0.0.1
API_PORT=5000
```

### Step 3: Set Up Python Virtual Environment
```powershell
# If script execution is restricted on Windows PowerShell, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create MySQL Database & Run Migrations
Open your MySQL client or terminal and create the database:
```sql
CREATE DATABASE IF NOT EXISTS meterguard_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Run Alembic database migrations to generate all required tables:
```powershell
python -m alembic -c backend/alembic.ini upgrade head
```

> [!IMPORTANT]
> Always execute Alembic using `python -m alembic -c backend/alembic.ini upgrade head` from the repository root to ensure the correct path configuration is used.

### Step 5: Set Up Frontend
```powershell
cd frontend
npm install
```

*(Optional)* To explicitly configure the backend API address for the frontend, create `frontend/.env`:
```ini
VITE_API_BASE_URL=http://127.0.0.1:5000
```
*(If omitted, Vite defaults to `http://localhost:5000` via `frontend/src/services/api.js`).*

```powershell
cd ..
```

---

## 9. Running the Application Locally

MeterGuard AI runs using a standard two-terminal workflow:

### Terminal 1: Backend API Server
```powershell
# From project root with virtual environment activated:
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000 --reload
```
- **Backend API:** `http://127.0.0.1:5000`
- **Interactive OpenAPI Documentation:** `http://127.0.0.1:5000/docs`
- Upon startup, the background simulation worker begins streaming `data/hardware_dataset.csv` automatically.

### Terminal 2: Frontend Development Server
```powershell
# In a second terminal:
cd frontend
npm run dev
```
- **Web Interface:** `http://localhost:5173`
- Open your browser to `http://localhost:5173` to access the full operational dashboard.

---

## 10. Core REST API Endpoints

| Method | Endpoint | Router | Description | Sample Parameters / Payload |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | `health.py` | Service and ML model readiness probe | *None* |
| `GET` | `/api/dashboard` | `dashboard.py` | Summary metrics & priority queue | *None* |
| `GET` | `/api/meters` | `dashboard.py` | Full registered meter list | *None* |
| `GET` | `/api/meter/{meter_id}` | `dashboard.py` | Meter telemetry and model states | Path: `meter_id` (`M001`, `M002`) |
| `POST` | `/api/meter-data` | `telemetry.py` | Ingests high-frequency electrical telemetry frame | `{"meter_id": "M001", "T1_CS": 2922, ...}` |
| `POST` | `/api/evaluate-sequence` | `anomaly.py` | Evaluates 30-day daily or 24-hr hourly sequence | `{"meter_id": "M001", "sequence_type": "daily", "consumption": [...]}` |
| `POST` | `/api/simulate/tamper` | `reports.py` | Injects synthetic 30-day tampering scenario | `{"meter_id": "M001", "scenario": "consumption_spike"}` |
| `GET` | `/api/alerts` | `dashboard.py` | Queries audited historical anomaly alerts | Query: `meter_id`, `severity`, `limit` |
| `POST` | `/api/reports/generate` | `reports.py` | Generates AI forensic investigation brief | `{"meter_id": "M001"}` |
| `GET` | `/api/simulation/status` | `simulation.py` | Queries dataset replay worker status | *None* |

---

## 11. Testing & Verification

The repository includes a suite of automated tests for backend logic, ML inference, and alert handling:

### 1. Complete Backend Integration Suite (Standalone)
Validates health probes, daily and hourly sequence inference, and all 10 edge-case input rejections without requiring a running server:
```powershell
python backend/test_backend_suite.py
```

### 2. Alert Lifecycle & Model Isolation Suite (Live API)
Verifies the 10-point alert lifecycle, guaranteeing Random Forest telemetry clears only RF alerts, sequence evaluations deduplicate properly, and scenario simulations remain isolated (requires backend running on `http://127.0.0.1:5000`):
```powershell
python backend/test_alert_lifecycle.py
```

### 3. Simulation Lifecycle Suite
Tests background dataset replay streaming, pausing, resuming, and speed adjustment:
```powershell
python backend/test_simulation_lifecycle.py
```

### 4. Six-Scenario ML Benchmark
Evaluates reconstruction errors across all six synthetic tampering profiles against calibrated thresholds:
```powershell
python backend/test_six_scenarios.py
```

### 5. Frontend Code Quality & Build Verification
Validates ESLint rules and builds the production bundle:
```powershell
npm --prefix frontend run lint
npm --prefix frontend run build
```

---

## 12. Known Limitations & Technical Context

1. **Software-First Simulation Platform:** MeterGuard AI is strictly an offline evaluation and simulation environment. It does not communicate with live Advanced Metering Infrastructure (AMI), headend systems, or utility SCADA networks.
2. **MinMaxScaler Error Attenuation on Daily Low-Consumption Scenarios:** As detailed mathematically in [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md), the Daily LSTM Autoencoder's global min-max scaling ($[2.92, 36.74]\text{ kWh}$) quadratically attenuates downward reconstruction errors. Complete meter flatlines achieve a theoretical maximum MSE of $0.007442$, which does not cross the calibrated $0.013009$ threshold. Physical energy diversion is instead caught via **Model 2 (Random Forest)** electrical current differentials.
3. **Synthetic Anomaly Scope:** Synthetic scenario evaluations demonstrate algorithmic behavior and threshold mechanics under controlled conditions; they do not represent statistical field performance across millions of live consumer accounts.
4. **Relational Database Dependency:** The application requires an active MySQL 8.0+ or MariaDB 10.5+ instance for relational persistence and alert audit logging.
