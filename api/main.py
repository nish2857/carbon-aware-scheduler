"""
FastAPI Web Application & REST API for Dynamic Carbon-Aware Cloud Workload Scheduler.
Run with: uvicorn api.main:app --reload --port 8000
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

# Ensure project root and current working directory are in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

try:
    from carbon_engine.grid_data_provider import GridDataProvider, REGION_METADATA
    from carbon_engine.forecaster import CarbonForecaster
    from scheduler_core.job_model import CloudJob, JobGenerator
    from scheduler_core.optimization_engine import CarbonAwareScheduler, SchedulerStrategy
except ModuleNotFoundError:
    from ..carbon_engine.grid_data_provider import GridDataProvider, REGION_METADATA
    from ..carbon_engine.forecaster import CarbonForecaster
    from ..scheduler_core.job_model import CloudJob, JobGenerator
    from ..scheduler_core.optimization_engine import CarbonAwareScheduler, SchedulerStrategy

app = FastAPI(
    title="Dynamic Carbon-Aware Cloud Workload Scheduler API",
    description="REST API for real-time grid carbon forecasting, dynamic spatial/temporal workload shifting, and multi-objective optimization.",
    version="1.0.0"
)

# Enable CORS for local React dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session cache for fast access
grid_provider = GridDataProvider(seed=42)
global_grid_df = grid_provider.generate_timeline_data(days=14)

split_idx = int(len(global_grid_df) * 0.7)
train_grid = global_grid_df.iloc[:split_idx]
test_grid = global_grid_df.iloc[split_idx:].reset_index(drop=True)

forecaster = CarbonForecaster(model_type='rf', seed=42)
forecaster.train(train_grid)
predicted_grid = forecaster.predict(test_grid)
full_test_df = pd.concat([test_grid, predicted_grid], axis=1)


class JobSubmitRequest(BaseModel):
    job_type: str = Field('AI Training', example='AI Training')
    power_kw: float = Field(150.0, example=150.0)
    duration: int = Field(4, example=4)
    max_delay: int = Field(12, example=12)
    priority: str = Field('Medium', example='Medium')
    allowed_regions: Optional[List[str]] = Field(None, example=['US-East-1', 'US-West-2', 'EU-Central-1'])


class SimulationRequest(BaseModel):
    num_jobs: int = Field(50, ge=10, le=300)
    simulation_days: int = Field(7, ge=2, le=30)
    strategy: SchedulerStrategy = Field(SchedulerStrategy.MIN_CARBON)
    carbon_weight: float = Field(0.5, ge=0.0, le=1.0)
    cost_weight: float = Field(0.3, ge=0.0, le=1.0)
    sla_weight: float = Field(0.2, ge=0.0, le=1.0)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Dynamic Carbon-Aware Cloud Workload Scheduler API",
        "version": "1.0.0",
        "active_regions": list(REGION_METADATA.keys())
    }


@app.get("/api/regions")
def get_regions():
    """Returns current metadata, live carbon intensity, price, and fuel mix for all regions."""
    latest_row = full_test_df.iloc[0]
    region_details = []

    for region_id, meta in REGION_METADATA.items():
        intensity = float(latest_row[f'{region_id}_carbon'])
        price = float(latest_row[f'{region_id}_price'])
        fuel_mix = grid_provider.get_region_fuel_mix(region_id, intensity)

        region_details.append({
            "region_id": region_id,
            "name": meta['name'],
            "location": meta['location'],
            "coordinates": meta['coordinates'],
            "primary_clean": meta['primary_clean'],
            "grid_type": meta['grid_type'],
            "current_carbon_intensity": round(intensity, 1),
            "current_electricity_price": round(price, 4),
            "fuel_mix": fuel_mix
        })

    return {"regions": region_details}


@app.get("/api/forecast")
def get_forecast(hours: int = Query(24, ge=6, le=72)):
    """Returns 24-48 hour carbon intensity forecasts for all global cloud regions."""
    subset = full_test_df.iloc[:hours]
    forecast_data = []

    for idx, row in subset.iterrows():
        entry = {
            "hour": int(row['hour']),
            "timestamp": str(row['timestamp'])
        }
        for r in REGION_METADATA.keys():
            entry[f"{r}_actual"] = round(float(row[f"{r}_carbon"]), 1)
            entry[f"{r}_predicted"] = round(float(row[f"{r}_predicted_carbon"]), 1)
            entry[f"{r}_price"] = round(float(row[f"{r}_price"]), 3)
        forecast_data.append(entry)

    return {
        "forecast_hours": hours,
        "data": forecast_data
    }


@app.post("/api/jobs/submit")
def submit_custom_job(req: JobSubmitRequest):
    """Submits and optimizes placement for an individual user job."""
    allowed = req.allowed_regions if req.allowed_regions else list(REGION_METADATA.keys())
    job = CloudJob(
        job_id="CUSTOM-001",
        job_type=req.job_type,
        submit_time=0,
        duration=req.duration,
        power_kw=req.power_kw,
        max_delay=req.max_delay,
        deadline=req.duration + req.max_delay,
        priority=req.priority,
        allowed_regions=allowed
    )

    scheduler = CarbonAwareScheduler(strategy=SchedulerStrategy.MIN_CARBON)
    result = scheduler.optimize_job_placement(job, full_test_df)
    return {"status": "success", "placement": result}


@app.post("/api/simulate")
def run_simulation(req: SimulationRequest):
    """Runs full comparative simulation across specified workload size and strategy."""
    jobs = JobGenerator(seed=42).generate_workload_queue(
        num_jobs=req.num_jobs,
        simulation_hours=min(len(full_test_df) - 12, req.simulation_days * 24)
    )

    scheduler = CarbonAwareScheduler(
        strategy=req.strategy,
        carbon_weight=req.carbon_weight,
        cost_weight=req.cost_weight,
        sla_weight=req.sla_weight
    )

    benchmark_results = scheduler.run_benchmark(jobs, full_test_df)

    # Convert DataFrames to dict lists for JSON response
    return {
        "status": "success",
        "summary": benchmark_results['summary'],
        "carbon_aware_jobs": benchmark_results['carbon_aware_results'].to_dict(orient='records'),
        "naive_jobs": benchmark_results['naive_results'].to_dict(orient='records')
    }


# Mount static files for frontend Web Dashboard UI
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
