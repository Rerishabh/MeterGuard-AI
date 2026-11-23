# MeterGuard AI: Frontend Web Application

The frontend for **MeterGuard AI** is a real-time utility monitoring dashboard built with React 19, Vite 8, Recharts, and Lucide React.

---

## 1. Application Architecture

The UI is structured around **four primary operational sections** and a persistent slide-in Settings drawer:

1. **Dashboard (`DashboardPage.jsx`):** High-level grid operations overview, summary metric cards, and the real-time **Account Investigation Priority Queue** (ranking accounts by `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` priority).
2. **AI Detection (`AiDetectionPage.jsx`):** Multi-model detection status cards (Isolation Forest, Random Forest, Daily LSTM, Hourly LSTM) and the interactive **Tampering Simulator** card.
3. **Live Telemetry (`LiveMonitoringPage.jsx`):** High-frequency line charts plotting real-time Transformer 1 ($T_1$), Pole Transformer ($T_2$), and Consumer ($H_1$) current, voltage, and power waveforms.
4. **Alerts & Logs (`AlertsLogsPage.jsx`):** Audited incident history displaying confirmed hardware faults and consumption sequence anomalies with full taxonomy labels (`SIMULATED_...`, `FAULT_...`) and status filtering.
5. **Settings Drawer (`SettingsPage.jsx`):** Slide-in panel accessed via the sidebar footer gear icon (`⚙`) for MySQL connection status, polling interval adjustment, and background simulation management.

---

## 2. Getting Started

### Prerequisites
- Node.js v18.0.0 or higher (v20+ recommended)
- npm v9+

### Installation
```bash
# From within the frontend/ directory:
npm install
```

### Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:5173`. By default, it communicates with the FastAPI backend at `http://localhost:5000`.

### Production Build & Linting
```bash
# Run ESLint verification (must report 0 errors)
npm run lint

# Compile production bundle
npm run build
```
Build outputs are written to `frontend/dist/`.

---

## 3. Configuration

Environment variables can be customized in `.env` (or via Vite proxy):
```ini
VITE_API_URL=http://localhost:5000
```
