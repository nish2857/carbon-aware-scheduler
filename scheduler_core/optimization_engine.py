"""
Multi-Objective Optimization Engine for Dynamic Carbon-Aware Cloud Scheduler.
Performs spatial and temporal workload shifting optimization and evaluates baseline benchmarks.
"""

import numpy as np
import pandas as pd
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional

from .job_model import CloudJob
from carbon_engine.grid_data_provider import REGION_METADATA

class SchedulerStrategy(str, Enum):
    MIN_CARBON = 'min_carbon'
    MIN_COST = 'min_cost'
    PARETO_BALANCED = 'pareto_balanced'

class CarbonAwareScheduler:
    """Core Scheduling Optimization Engine."""

    def __init__(self, strategy: SchedulerStrategy = SchedulerStrategy.MIN_CARBON,
                 carbon_weight: float = 0.5, cost_weight: float = 0.3, sla_weight: float = 0.2):
        self.strategy = strategy
        self.carbon_weight = carbon_weight
        self.cost_weight = cost_weight
        self.sla_weight = sla_weight

    def _calculate_window_metrics(self, job: CloudJob, start_t: int, region: str,
                                  carbon_df: pd.DataFrame, is_forecast: bool = True) -> Tuple[float, float]:
        """Calculates expected emissions (gCO2eq) and cost ($) for a job running in region from start_t for duration."""
        end_t = start_t + job.duration
        total_emissions_g = 0.0
        total_cost_usd = 0.0

        carbon_col = f'{region}_predicted_carbon' if is_forecast and f'{region}_predicted_carbon' in carbon_df.columns else f'{region}_carbon'
        price_col = f'{region}_price'

        for t in range(start_t, min(end_t, len(carbon_df))):
            intensity = carbon_df.loc[t, carbon_col] # gCO2eq/kWh
            price = carbon_df.loc[t, price_col] if price_col in carbon_df.columns else REGION_METADATA[region]['base_cost']

            # Energy kWh = power_kw * 1 hour
            total_emissions_g += intensity * job.power_kw
            total_cost_usd += price * job.power_kw

        return total_emissions_g, total_cost_usd

    def optimize_job_placement(self, job: CloudJob, carbon_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Finds optimal (region, start_time) pair for a single job according to selected strategy.
        """
        submit_t = job.submit_time
        max_start = submit_t + job.max_delay
        candidate_regions = job.allowed_regions if job.allowed_regions else list(REGION_METADATA.keys())

        best_score = float('inf')
        best_region = candidate_regions[0]
        best_start = submit_t
        best_emissions_g = float('inf')
        best_cost_usd = float('inf')

        # Baseline normalization factors for Pareto scoring
        base_emissions, base_cost = self._calculate_window_metrics(job, submit_t, 'US-East-1', carbon_df)
        base_emissions = max(1.0, base_emissions)
        base_cost = max(0.01, base_cost)

        for region in candidate_regions:
            for start_t in range(submit_t, min(max_start + 1, len(carbon_df) - job.duration)):
                emissions_g, cost_usd = self._calculate_window_metrics(job, start_t, region, carbon_df, is_forecast=True)
                delay_hours = start_t - submit_t

                if self.strategy == SchedulerStrategy.MIN_CARBON:
                    score = emissions_g

                elif self.strategy == SchedulerStrategy.MIN_COST:
                    score = cost_usd

                elif self.strategy == SchedulerStrategy.PARETO_BALANCED:
                    norm_carbon = emissions_g / base_emissions
                    norm_cost = cost_usd / base_cost
                    norm_delay = delay_hours / max(1, job.max_delay) if job.max_delay > 0 else 0.0

                    score = (self.carbon_weight * norm_carbon +
                             self.cost_weight * norm_cost +
                             self.sla_weight * norm_delay)

                if score < best_score:
                    best_score = score
                    best_region = region
                    best_start = start_t
                    best_emissions_g = emissions_g
                    best_cost_usd = cost_usd

        # Calculate GROUND TRUTH actual emissions & cost with actual data
        actual_emissions_g, actual_cost_usd = self._calculate_window_metrics(job, best_start, best_region, carbon_df, is_forecast=False)

        return {
            'job_id': job.job_id,
            'job_type': job.job_type,
            'priority': job.priority,
            'assigned_region': best_region,
            'submit_time': submit_t,
            'scheduled_start_time': best_start,
            'delay_hours': best_start - submit_t,
            'max_delay_allowed': job.max_delay,
            'duration': job.duration,
            'power_kw': job.power_kw,
            'predicted_emissions_kg': round(best_emissions_g / 1000.0, 3),
            'actual_emissions_kg': round(actual_emissions_g / 1000.0, 3),
            'actual_cost_usd': round(actual_cost_usd, 2),
            'sla_violated': best_start > (submit_t + job.max_delay)
        }

    def run_benchmark(self, jobs: List[CloudJob], carbon_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs comprehensive comparative benchmark across 3 scheduling approaches:
        1. Naive Immediate (Fixed local region US-East-1, no delay)
        2. Temporal-Only Shifting (Fixed region US-East-1, delayed to optimal hour)
        3. Dynamic Carbon-Aware (Spatial + Temporal Shifting)
        """
        # 1. Naive Immediate
        naive_records = []
        for j in jobs:
            start_t = j.submit_time
            if start_t + j.duration < len(carbon_df):
                em_g, cost = self._calculate_window_metrics(j, start_t, 'US-East-1', carbon_df, is_forecast=False)
                naive_records.append({
                    'job_id': j.job_id,
                    'region': 'US-East-1',
                    'start_time': start_t,
                    'emissions_kg': em_g / 1000.0,
                    'cost_usd': cost
                })

        # 2. Temporal Only
        temporal_records = []
        for j in jobs:
            submit_t = j.submit_time
            max_start = submit_t + j.max_delay
            best_t = submit_t
            best_em = float('inf')
            best_cost = float('inf')
            for start_t in range(submit_t, min(max_start + 1, len(carbon_df) - j.duration)):
                em_g, cost = self._calculate_window_metrics(j, start_t, 'US-East-1', carbon_df, is_forecast=True)
                if em_g < best_em:
                    best_em = em_g
                    best_t = start_t
                    best_cost = cost
            actual_em, actual_cost = self._calculate_window_metrics(j, best_t, 'US-East-1', carbon_df, is_forecast=False)
            temporal_records.append({
                'job_id': j.job_id,
                'region': 'US-East-1',
                'start_time': best_t,
                'delay_hours': best_t - submit_t,
                'emissions_kg': actual_em / 1000.0,
                'cost_usd': actual_cost
            })

        # 3. Dynamic Carbon-Aware (Spatial + Temporal)
        ca_records = []
        region_counts = {}
        for j in jobs:
            res = self.optimize_job_placement(j, carbon_df)
            ca_records.append(res)
            r = res['assigned_region']
            region_counts[r] = region_counts.get(r, 0) + 1

        # Calculate summary metrics
        naive_em_total = sum(r['emissions_kg'] for r in naive_records)
        naive_cost_total = sum(r['cost_usd'] for r in naive_records)

        temp_em_total = sum(r['emissions_kg'] for r in temporal_records)
        temp_cost_total = sum(r['cost_usd'] for r in temporal_records)

        ca_em_total = sum(r['actual_emissions_kg'] for r in ca_records)
        ca_cost_total = sum(r['actual_cost_usd'] for r in ca_records)

        sla_violations = sum(1 for r in ca_records if r['sla_violated'])

        emissions_saved_kg = max(0.0, naive_em_total - ca_em_total)
        emissions_reduction_pct = (emissions_saved_kg / naive_em_total * 100.0) if naive_em_total > 0 else 0.0

        cost_saved_usd = max(0.0, naive_cost_total - ca_cost_total)
        cost_reduction_pct = (cost_saved_usd / naive_cost_total * 100.0) if naive_cost_total > 0 else 0.0

        return {
            'summary': {
                'total_jobs': len(jobs),
                'naive_emissions_kg': round(naive_em_total, 2),
                'naive_cost_usd': round(naive_cost_total, 2),
                'temporal_emissions_kg': round(temp_em_total, 2),
                'temporal_cost_usd': round(temp_cost_total, 2),
                'carbon_aware_emissions_kg': round(ca_em_total, 2),
                'carbon_aware_cost_usd': round(ca_cost_total, 2),
                'emissions_saved_kg': round(emissions_saved_kg, 2),
                'emissions_reduction_pct': round(emissions_reduction_pct, 2),
                'cost_saved_usd': round(cost_saved_usd, 2),
                'cost_reduction_pct': round(cost_reduction_pct, 2),
                'sla_compliance_pct': round(((len(jobs) - sla_violations) / len(jobs)) * 100.0, 2),
                'region_distribution': region_counts
            },
            'naive_results': pd.DataFrame(naive_records),
            'temporal_results': pd.DataFrame(temporal_records),
            'carbon_aware_results': pd.DataFrame(ca_records)
        }


if __name__ == '__main__':
    from carbon_engine.grid_data_provider import GridDataProvider
    from carbon_engine.forecaster import CarbonForecaster
    from scheduler_core.job_model import JobGenerator

    provider = GridDataProvider()
    df = provider.generate_timeline_data(days=14)

    split = int(len(df) * 0.7)
    train_df = df.iloc[:split]
    test_df = df.iloc[split:].reset_index(drop=True)

    forecaster = CarbonForecaster()
    forecaster.train(train_df)
    forecast_preds = forecaster.predict(test_df)
    full_test_df = pd.concat([test_df, forecast_preds], axis=1)

    jobs = JobGenerator().generate_workload_queue(num_jobs=50, simulation_hours=len(test_df))

    scheduler = CarbonAwareScheduler(strategy=SchedulerStrategy.MIN_CARBON)
    results = scheduler.run_benchmark(jobs, full_test_df)

    print("=== BENCHMARK RESULTS SUMMARY ===")
    for k, v in results['summary'].items():
        print(f"{k}: {v}")
