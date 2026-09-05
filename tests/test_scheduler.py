"""
Automated Unit and Integration Test Suite for Dynamic Carbon-Aware Cloud Workload Scheduler.
"""

import unittest
import pandas as pd
import numpy as np

from carbon_engine.grid_data_provider import GridDataProvider, REGION_METADATA
from carbon_engine.forecaster import CarbonForecaster
from scheduler_core.job_model import CloudJob, JobGenerator
from scheduler_core.optimization_engine import CarbonAwareScheduler, SchedulerStrategy

class TestCarbonAwareScheduler(unittest.TestCase):

    def setUp(self):
        self.provider = GridDataProvider(seed=42)
        self.grid_df = self.provider.generate_timeline_data(days=7)
        self.job_gen = JobGenerator(seed=42)
        self.jobs = self.job_gen.generate_workload_queue(num_jobs=20, simulation_hours=len(self.grid_df))

    def test_grid_data_provider_structure(self):
        """Verify grid carbon intensity data contains all 6 regions."""
        self.assertGreater(len(self.grid_df), 0)
        for region in REGION_METADATA.keys():
            self.assertIn(f'{region}_carbon', self.grid_df.columns)
            self.assertIn(f'{region}_price', self.grid_df.columns)
            # Assert non-negative carbon and pricing values
            self.assertTrue((self.grid_df[f'{region}_carbon'] >= 0).all())
            self.assertTrue((self.grid_df[f'{region}_price'] > 0).all())

    def test_fuel_mix_percentage_total(self):
        """Verify fuel mix percentages sum up to 100%."""
        mix = self.provider.get_region_fuel_mix('US-East-1', carbon_intensity=400.0)
        total_pct = sum(mix.values())
        self.assertAlmostEqual(total_pct, 100.0, delta=1.0)

    def test_ml_forecaster_training(self):
        """Verify CarbonForecaster trains and generates predictions without NaNs."""
        split = int(len(self.grid_df) * 0.7)
        train_df = self.grid_df.iloc[:split]
        test_df = self.grid_df.iloc[split:].reset_index(drop=True)

        forecaster = CarbonForecaster(seed=42)
        metrics = forecaster.train(train_df)
        self.assertIn('US-East-1', metrics)
        self.assertGreater(metrics['US-East-1']['r2'], 0.5)

        preds = forecaster.predict(test_df)
        self.assertEqual(len(preds), len(test_df))
        self.assertFalse(preds.isna().any().any())

    def test_scheduler_optimization_reduction(self):
        """Verify Carbon-Aware Scheduler achieves emission reduction vs naive baseline."""
        forecaster = CarbonForecaster(seed=42)
        split = int(len(self.grid_df) * 0.7)
        forecaster.train(self.grid_df.iloc[:split])
        preds = forecaster.predict(self.grid_df.iloc[split:].reset_index(drop=True))
        test_df = pd.concat([self.grid_df.iloc[split:].reset_index(drop=True), preds], axis=1)

        scheduler = CarbonAwareScheduler(strategy=SchedulerStrategy.MIN_CARBON)
        results = scheduler.run_benchmark(self.jobs, test_df)

        summary = results['summary']
        self.assertLess(summary['carbon_aware_emissions_kg'], summary['naive_emissions_kg'])
        self.assertGreater(summary['emissions_reduction_pct'], 10.0)

    def test_sla_deadline_enforcement(self):
        """Verify critical jobs with hard SLA deadlines are never violated."""
        critical_job = CloudJob(
            job_id="TEST-CRIT-01",
            job_type="AI Training",
            submit_time=0,
            duration=2,
            power_kw=100.0,
            max_delay=0, # Hard deadline, zero delay allowed
            deadline=2,
            priority="Critical"
        )
        scheduler = CarbonAwareScheduler()
        res = scheduler.optimize_job_placement(critical_job, self.grid_df)
        self.assertEqual(res['delay_hours'], 0)
        self.assertFalse(res['sla_violated'])


if __name__ == '__main__':
    unittest.main()
