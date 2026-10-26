# Gridwise AI — Smart Energy Microgrid & Demand Forecasting Engine
> **HackSphere 3.0** | Zoho Catalyst & QuickML Track  
> **Authors / Team:** Gridwise Engineering Team  
> **Repository:** [https://github.com/gouravsharmaswe-ship-it/hack-sphere-gridwise-ai](https://github.com/gouravsharmaswe-ship-it/hack-sphere-gridwise-ai)

---

## 1. Executive Summary & Problem Overview

Modern renewable microgrids require real-time, high-fidelity energy demand forecasting to balance intermittent generation (solar/wind), avoid sudden grid collapses, and schedule energy storage transitions. 

**Gridwise AI** is an end-to-end intelligent microgrid decision-support engine designed for **Zoho Catalyst**. It consumes hourly weather telemetry (ambient temperature, humidity, solar irradiance), forecasts 24-hour ahead electrical load (kW), and evaluates deterministic operational rules to trigger automated power transitions:
1. **Renewable Storage Mode**: Dispatches localized battery storage during peak demand (> 160 kW) or critical evening peak hours (18:00–22:00 inclusive) to shave main grid peaks.
2. **Main Grid Mode**: Restores main utility grid power during nominal, off-peak periods (&le; 160 kW, outside 18:00–22:00).
3. **Critical Overload Alert**: Independently flags any hour where predicted demand breaches 200 kW (&ge; 200 kW), signaling operators to implement emergency curtailment or reserve dispatch.

---

## 2. Architecture & Catalyst Services

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             Zoho Catalyst                                │
├───────────────────────────────┬──────────────────────────────────────────┤
│         Catalyst Slate        │             Catalyst AppSail             │
│   (React + TypeScript UI)     │          (FastAPI Python Engine)         │
│                               │                                          │
│  - 24h Interactive Load Curve │  - REST Endpoints (/api/forecast/24h)    │
│  - Dispatch Timeline Table    │  - Deterministic Transition Controller   │
│  - Critical Overload Banners  │  - Input Validation & Schema Guard       │
│  - CSV Telemetry Ingestion    │  - SQLite / Catalyst Data Store          │
│  - Scenario Simulator         │                                          │
└───────────────▲───────────────┴────────────────────▲─────────────────────┘
                │ HTTP Proxy                         │ HTTPS REST
                ▼                                    ▼
    ┌──────────────────────┐             ┌─────────────────────────┐
    │  Browser Dashboard   │             │ Zoho Catalyst QuickML   │
    │  (Desktop & Mobile)  │             │ Regression Inference    │
    └──────────────────────┘             └─────────────────────────┘
```

| Component | Technology / Catalyst Service | Role |
| :--- | :--- | :--- |
| **Telemetry Ingestion** | Catalyst Slate / REST API | Validates uploaded CSVs or scenario inputs with strict Pydantic guards. |
| **Prediction Pipeline** | Zoho Catalyst QuickML / AppSail | Executes regression inference returning 24 consecutive hourly predictions. |
| **Transition Controller**| Python `core/dispatch_rules.py` | Deterministic logic: 160 kW threshold, 18–22 peak hours, 200 kW overload alert. |
| **Dashboard UI** | React 18, TypeScript, Vite, Recharts | Energy-analytics operator dashboard with visual reference lines. |
| **Audit Persistence** | SQLite (Local) / Catalyst Data Store | Durable history of past forecasts and downloadable CSV predictions. |

---

## 3. Dataset Schema & Empirical Model Evaluation

### Telemetry Schema
| Column | Type | Units | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` | String | `YYYY-MM-DD HH:MM:SS` | Hourly timestamp (exact 3,600s interval). |
| `ambient_temp_c` | Float | °C | Outdoor ambient temperature (-1.4°C to 38.3°C). |
| `humidity_pct` | Float | % | Relative humidity percentage (39.3% to 100.0%). |
| `solar_irradiance_wm2` | Float | W/m² | Solar potential (0 to 488 W/m²). |
| `target_demand_kw` | Float | kW | Target load demand (51.1 kW to 306.3 kW). |

### Chronological Holdout Evaluation Methodology
To prevent data leakage and simulate genuine production forecasting, observations were split **chronologically** (never randomly shuffled):
- **Training Set**: First 3,200 consecutive hours (2014-12-31 23:00 to 2015-05-14 06:00, 80% split).
- **Holdout Test Set**: Last 800 consecutive hours (2015-05-14 07:00 to 2015-06-16 14:00, 20% split).

### Verified Benchmark Results
| Model Candidate | Holdout RMSE | Holdout MAE | Holdout $R^2$ | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Hourly Seasonal Mean Baseline** | 48.76 kW | 40.39 kW | 0.364 | Naive baseline |
| **Starter Formula Baseline** | 45.85 kW | 31.21 kW | 0.437 | Starter kit baseline |
| **Ridge Regression Pipeline** | 27.85 kW | 21.47 kW | 0.792 | Linear baseline |
| **Gradient Boosting Pipeline** | **12.47 kW** | **9.80 kW** | **0.958** | **Production Local Model** |
| **Zoho Catalyst QuickML Endpoint** | *Live API* | *Live API* | *Live API* | **Supported Cloud Model** |

---

## 4. Transition Controller Rules

Implemented in `core/dispatch_rules.py` and strictly unit tested:

1. **Renewable Storage Mode**:
   - `predicted_demand_kw > 160.0` **OR** `18 <= local_hour <= 22`
2. **Main Grid Mode**:
   - `predicted_demand_kw <= 160.0` **AND** (`local_hour < 18` or `local_hour > 22`)
3. **Critical Overload Alert**:
   - Independently triggered whenever `predicted_demand_kw >= 200.0 kW`.
   - *Independent of dispatch mode:* A demand of 220 kW at 14:00 selects Renewable Storage Mode AND triggers a Critical Overload Alert.

---

## 5. Official Prediction Contract & CLI Verification

### Python Function Contract
```python
from predict import predict
import pandas as pd

df = pd.read_csv("sample_test_input.csv")
predictions = predict(df)
# Returns numpy.ndarray with exactly len(df) finite float predictions
```

### CLI Command
```bash
python predict.py --input sample_test_input.csv --output predictions.csv
```
The output `predictions.csv` strictly contains:
```csv
timestamp,target_demand_kw
2015-06-16 15:00:00,243.13
2015-06-16 16:00:00,234.47
```

### Pre-Submission Self-Test
```bash
python test_eval.py
```
Outputs: `SUCCESS`

---

## 6. Local Quickstart Guide

### Prerequisites
- Python 3.9+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# In project root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start FastAPI server on port 8000
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 3. Run Automated Tests
```bash
# In project root with active venv:
pytest backend/tests/ -v
python test_eval.py
```
Result: **21/21 Automated Tests Pass!**

---

## 7. Connecting to Zoho Catalyst QuickML

To direct inference to your published Catalyst QuickML model endpoint:

1. Open your Zoho Catalyst Console -> **AI / QuickML**.
2. Upload `train_telemetry.csv` and configure `target_demand_kw` as the regression target.
3. Train the model and click **Publish**.
4. Set the environment variables in `.env`:
   ```env
   QUICKML_ENDPOINT_URL=https://ml.catalyst.zoho.com/baas/v1/project/<PROJECT_ID>/model/<MODEL_ID>/predict
   QUICKML_API_KEY=<YOUR_CATALYST_OAUTH_TOKEN>
   ```
5. Restart the backend. The dashboard and `predict.py` will route inference directly to QuickML.

---

## 8. Deployment on Zoho Catalyst AppSail & Slate

The repository includes pre-configured Catalyst deployment manifests:
- `catalyst.json`: Declares the Slate client build (`frontend/dist`) and AppSail backend (`gridwise-engine`).
- `app-config.json`: Declares the AppSail startup command:
  ```json
  {
    "command": "uvicorn backend.main:app --host 0.0.0.0 --port $X_ZOHO_CATALYST_LISTEN_PORT",
    "stack": "python",
    "version": "3.9"
  }
  ```

### Deployment Steps:
```bash
# 1. Build frontend distribution
cd frontend && npm run build && cd ..

# 2. Deploy using Catalyst CLI
catalyst deploy
```

---

## 9. Likely Judge Questions & Technical Answers

**Q1: How do you prevent time-series data leakage in your ML pipeline?**  
*Answer:* We use strict chronological splitting. The holdout test set consists of the last 800 consecutive hours (`2015-05-14` to `2015-06-16`), entirely distinct from the first 3,200 training hours. No future rolling windows or future lag features are used during training or inference.

**Q2: What happens if the external QuickML endpoint times out or returns HTTP 500?**  
*Answer:* In adherence to the problem contract, when an external endpoint is configured and fails, `predict.py` raises a `ModelInferenceError` and exits with non-zero exit code. It never silently returns fake numbers. In the web dashboard, the adapter reports `configured_unreachable` with the real error message and allows the operator to inspect the failure or fall back to the audited local pipeline.

**Q3: Why are Critical Overload Alerts independent of Dispatch Mode?**  
*Answer:* Power system safety requires decoupling operational dispatch from emergency warnings. Renewable Storage Mode is scheduled during peak periods to reduce utility costs, but an overload (&ge; 200 kW) represents a physical safety risk that requires immediate alert notification regardless of which power source is active.

---

## 10. License & Disclaimers
This project was developed for **HackSphere 3.0**.  
*Disclaimer:* Gridwise AI is a decision-support and demand-forecasting software tool. It provides automated operational recommendations and does not directly control physical high-voltage grid switchgear.
