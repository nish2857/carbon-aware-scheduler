"""
Machine Learning & Optimization Engine for Carbon-Aware Cloud Workload Scheduler.
Includes ML forecasting of grid carbon intensity and spatial/temporal optimization.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

from data_generator import generate_grid_carbon_data, generate_job_queue

class CarbonForecaster:
    """ML Model for predicting hourly grid carbon intensity across regions."""
    def __init__(self, regions=['US-East', 'US-West', 'EU-Central', 'AP-South']):
        self.regions = regions
        self.models = {r: RandomForestRegressor(n_estimators=100, random_state=42) for r in regions}
        
    def _create_features(self, df, region):
        features = pd.DataFrame(index=df.index)
        features['hour'] = df['hour']
        features['day_of_week'] = df['day_of_week']
        features['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24.0)
        features['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24.0)
        features['lag_1h'] = df[region].shift(1).bfill()
        features['lag_24h'] = df[region].shift(24).bfill()
        features['rolling_6h'] = df[region].rolling(6, min_periods=1).mean()
        return features

    def train(self, df_train):
        for region in self.regions:
            X = self._create_features(df_train, region)
            y = df_train[region]
            self.models[region].fit(X, y)
            
    def predict(self, df):
        predictions = {}
        for region in self.regions:
            X = self._create_features(df, region)
            predictions[region] = self.models[region].predict(X)
        return pd.DataFrame(predictions, index=df.index)

def run_scheduler_simulation(grid_df, jobs_df):
    """
    Simulates naive vs carbon-aware scheduling over grid intensity data.
    """
    regions = ['US-East', 'US-West', 'EU-Central', 'AP-South']
    
    # Train/Test split for ML forecaster
    split_idx = int(len(grid_df) * 0.5)
    train_df = grid_df.iloc[:split_idx]
    test_df = grid_df.iloc[split_idx:].reset_index(drop=True)
    
    forecaster = CarbonForecaster(regions)
    forecaster.train(train_df)
    predicted_carbon = forecaster.predict(test_df)
    
    # Baseline Naive Scheduler (Executes immediately in default region US-East)
    naive_results = []
    total_naive_emissions_g = 0.0
    
    for _, job in jobs_df.iterrows():
        start_t = job['submit_time']
        end_t = start_t + job['duration']
        
        # Ensure within test timeline
        if end_t >= len(test_df):
            continue
            
        emissions = 0.0
        for t in range(start_t, end_t):
            actual_intensity = test_df.loc[t, 'US-East'] # gCO2eq/kWh
            # Energy in kWh = power_kw * 1 hour
            emissions += actual_intensity * job['power_kw']
            
        total_naive_emissions_g += emissions
        naive_results.append({
            'job_id': job['job_id'],
            'region': 'US-East',
            'start_time': start_t,
            'emissions_g': emissions
        })
        
    # Proposed ML Carbon-Aware Scheduler (Spatial + Temporal Shifting)
    carbon_aware_results = []
    total_ca_emissions_g = 0.0
    sla_violations = 0
    region_counts = {r: 0 for r in regions}
    
    for _, job in jobs_df.iterrows():
        submit_t = job['submit_time']
        duration = job['duration']
        max_start = submit_t + job['max_delay']
        
        best_cost = float('inf')
        best_region = 'US-East'
        best_start = submit_t
        
        # Search all regions and valid time windows
        for r in regions:
            for start_t in range(submit_t, min(max_start + 1, len(test_df) - duration)):
                end_t = start_t + duration
                # Use ML Predicted Carbon Intensity for decision making!
                predicted_emissions = 0.0
                for t in range(start_t, end_t):
                    predicted_emissions += predicted_carbon.loc[t, r] * job['power_kw']
                    
                if predicted_emissions < best_cost:
                    best_cost = predicted_emissions
                    best_region = r
                    best_start = start_t
                    
        # Calculate actual emissions with ground truth carbon data
        actual_emissions = 0.0
        for t in range(best_start, best_start + duration):
            actual_emissions += test_df.loc[t, best_region] * job['power_kw']
            
        if best_start > submit_t + job['max_delay']:
            sla_violations += 1
            
        region_counts[best_region] += 1
        total_ca_emissions_g += actual_emissions
        
        carbon_aware_results.append({
            'job_id': job['job_id'],
            'region': best_region,
            'start_time': best_start,
            'delay_hours': best_start - submit_t,
            'emissions_g': actual_emissions
        })
        
    naive_kg = total_naive_emissions_g / 1000.0
    ca_kg = total_ca_emissions_g / 1000.0
    reduction_pct = ((naive_kg - ca_kg) / naive_kg) * 100.0
    
    # Calculate ML forecasting error metrics
    rmse_scores = {}
    for r in regions:
        rmse_scores[r] = np.sqrt(mean_squared_error(test_df[r], predicted_carbon[r]))
        
    metrics = {
        'naive_emissions_kg': round(naive_kg, 2),
        'carbon_aware_emissions_kg': round(ca_kg, 2),
        'saved_emissions_kg': round(naive_kg - ca_kg, 2),
        'reduction_percentage': round(reduction_pct, 2),
        'sla_violations': sla_violations,
        'total_jobs_evaluated': len(naive_results),
        'region_distribution': region_counts,
        'forecasting_rmse': {r: round(val, 2) for r, val in rmse_scores.items()}
    }
    
    return metrics, pd.DataFrame(naive_results), pd.DataFrame(carbon_aware_results), test_df

if __name__ == '__main__':
    grid = generate_grid_carbon_data()
    jobs = generate_job_queue()
    metrics, naive_df, ca_df, test_grid = run_scheduler_simulation(grid, jobs)
    print("=== SIMULATION METRICS ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")
