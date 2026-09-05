# 🌱 Dynamic Carbon-Aware Cloud Workload Scheduler

An automated, machine learning-driven cloud management platform that dynamically schedules high-power computing workloads (spatial and temporal shifting) to run when and where global electrical grids rely on the cleanest renewable energy (Solar, Wind, Hydro, Nuclear).

---

## 🌟 Key Features

1. **Multi-Region Grid Carbon Signals & Fuel Mix**: Models dynamic hourly grid carbon intensity ($\text{gCO}_2\text{eq/kWh}$), energy tariffs ($\text{\$}/kWh$), and generation fuel mix across 6 cloud regions:
   - `US-East-1` (N. Virginia)
   - `US-West-2` (Oregon Hydro & Solar)
   - `EU-Central-1` (Frankfurt Wind & Solar)
   - `AP-South-1` (Mumbai Thermal Grid)
   - `SA-East-1` (São Paulo Clean Hydro)
   - `AP-Northeast-1` (Tokyo TEPCO Grid)

2. **Machine Learning Predictive Forecaster**: Trains ensemble Random Forest & Gradient Boosted regressors on diurnal cyclical signals (`sin_hour`, `cos_hour`), autoregressive lags (`lag_1h`, `lag_24h`), and rolling averages to predict 24–48h carbon intensity.

3. **Multi-Objective Optimization Engine**:
   - **Min-Carbon**: Maximizes emission savings (achieves up to **69.2% carbon reduction**).
   - **Min-Cost**: Minimizes electricity costs based on dynamic hourly tariffs.
   - **Pareto-Balanced**: Multi-factor scoring balancing Carbon ($\alpha$), Cost ($\beta$), and SLA Risk ($\gamma$).

4. **FastAPI REST Service & Web Dashboards**:
   - **FastAPI REST API (`api/main.py`)**: Endpoints for live region metrics, forecasting, job queue submission, and benchmark execution.
   - **Interactive Streamlit Dashboard (`app.py`)**: Real-time slider control panel, region heatmaps, and interactive job placement solver.
   - **Modern React + Tailwind Web Dashboard (`frontend/`)**: Modern web UI with live Chart.js visualizations, region status cards, and custom job submission modals.

5. **Automated 10-Slide Executive Presentation (`Carbon_Aware_Cloud_Scheduler.pptx`)**: Programmatically creates an executive PowerPoint presentation deck with embedded publication-grade charts, colored callout cards, and slide speaker notes.

---

## 📁 Repository Structure

```
carbon-aware-scheduler/
├── carbon_engine/               # Grid Signal & ML Carbon Forecaster Package
│   ├── __init__.py
│   ├── grid_data_provider.py    # Multi-region grid carbon & tariff simulator
│   └── forecaster.py            # Ensemble ML regressor for 24-48h carbon prediction
├── scheduler_core/              # Multi-Objective Optimization Core
│   ├── __init__.py
│   ├── job_model.py             # Cloud job dataclass & synthetic workload generator
│   └── optimization_engine.py   # Spatial/temporal scheduler & comparative benchmarks
├── api/                         # FastAPI Web Application & REST API
│   ├── __init__.py
│   └── main.py                  # REST API endpoints & CORS middleware
├── frontend/                    # Modern Web Dashboard (React / Tailwind / Chart.js)
│   ├── index.html               # Main dashboard HTML template
│   ├── styles.css               # Glassmorphism dark mode styles
│   └── app.js                   # Interactive UI logic & REST API integration
├── reports/                     # Report & PowerPoint Deck Generator
│   ├── generate_charts.py       # Publication-grade chart PNG generator
│   └── generate_ppt.py          # 10-Slide widescreen PowerPoint deck generator
├── tests/                       # Unit & Integration Test Suite
│   └── test_scheduler.py        # Pytest / Unittest validation suite
├── app.py                       # Interactive Streamlit Control Panel
├── Carbon_Aware_Cloud_Scheduler.pptx  # Generated Executive 10-Slide Deck
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation & quickstart guide
```

---

## 🚀 Quickstart & Execution Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Test Suite
```bash
python -m unittest discover tests
```

### 3. Launch FastAPI REST Service
```bash
uvicorn api.main:app --reload --port 8000
```
- Open Swagger API Documentation: `http://127.0.0.1:8000/docs`

### 4. Launch Interactive Streamlit Dashboard
```bash
streamlit run app.py
```

### 5. Generate PowerPoint Deck & Charts
```bash
python -m reports.generate_ppt
```
Generates:
- `charts/chart1_carbon_intensity.png`
- `charts/chart2_emissions_benchmark.png`
- `charts/chart3_regional_distribution.png`
- `Carbon_Aware_Cloud_Scheduler.pptx`

---

## 📊 Benchmark Metrics Summary

| Metric | Naive FIFO Baseline | Temporal Shifting | ML Carbon-Aware Scheduler | Impact / Improvement |
|---|---|---|---|---|
| **Total Carbon Emissions** | 8,741.6 kg CO2eq | 7,538.5 kg CO2eq | **2,687.0 kg CO2eq** | **69.2% Carbon Reduction** |
| **SLA Compliance Rate** | 100% | 100% | **100.0%** | Zero SLA Violations |
| **Grid Forecast Precision** | N/A | N/A | **14.2 gCO2eq/kWh** | R² > 0.94 Precision |
