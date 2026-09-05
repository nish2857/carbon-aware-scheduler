"""
Data Generator for Dynamic Carbon-Aware Cloud Workload Scheduler.
Generates multi-region hourly grid carbon intensity data (gCO2eq/kWh)
and realistic batch workload job queues.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_grid_carbon_data(days=14, seed=42):
    """
    Generates 24*days hours of carbon intensity (gCO2eq/kWh) for 4 cloud regions:
    - US-East (Coal/Gas dominant, moderate solar)
    - US-West (High Solar peak in afternoon)
    - EU-Central (High Wind & Nuclear, low carbon overall)
    - AP-South (High Coal, sharp peaks)
    """
    np.random.seed(seed)
    hours = days * 24
    timestamps = [datetime(2026, 8, 1) + timedelta(hours=i) for i in range(hours)]
    
    time_of_day = np.array([t.hour for t in timestamps])
    
    # Base profiles + diurnal patterns
    # US-East: Base 420, dip at noon due to solar (dip of 80)
    us_east = 420 - 80 * np.sin((time_of_day - 6) * np.pi / 12).clip(0, 1) + np.random.normal(0, 15, hours)
    
    # US-West: Base 300, strong solar dip at noon (dip of 180)
    us_west = 300 - 180 * np.sin((time_of_day - 7) * np.pi / 12).clip(0, 1) + np.random.normal(0, 20, hours)
    
    # EU-Central: Base 180, wind variation + morning/evening demand peaks
    eu_central = 180 + 40 * np.sin((time_of_day - 8) * np.pi / 6) + np.random.normal(0, 25, hours)
    
    # AP-South: Base 550, high emissions during evening peak hours (18-22)
    ap_south = 550 + 70 * (time_of_day >= 18) * (time_of_day <= 22) + np.random.normal(0, 18, hours)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'hour': time_of_day,
        'day_of_week': [t.weekday() for t in timestamps],
        'US-East': np.clip(us_east, 100, 700),
        'US-West': np.clip(us_west, 50, 600),
        'EU-Central': np.clip(eu_central, 30, 450),
        'AP-South': np.clip(ap_south, 200, 850)
    })
    
    return df

def generate_job_queue(num_jobs=100, simulation_hours=48, seed=42):
    """
    Generates synthetic cloud batch workloads.
    Each job has submission time, duration (hours), power consumption (kW),
    and max allowed delay (SLA in hours).
    """
    np.random.seed(seed)
    
    job_types = ['AI Training', 'Data Processing', 'Video Encoding', 'Database Backup', 'Genomics Pipeline']
    
    jobs = []
    for i in range(1, num_jobs + 1):
        submit_time = np.random.randint(0, simulation_hours - 12)
        duration = np.random.choice([1, 2, 3, 4, 6, 8], p=[0.3, 0.25, 0.2, 0.1, 0.1, 0.05])
        max_delay = np.random.choice([2, 4, 6, 12, 18, 24], p=[0.2, 0.25, 0.25, 0.15, 0.1, 0.05])
        power_kw = np.random.uniform(10.0, 100.0) # Server cluster power draw in kW
        job_type = np.random.choice(job_types)
        
        jobs.append({
            'job_id': f'JOB-{i:03d}',
            'job_type': job_type,
            'submit_time': submit_time,
            'duration': duration,
            'max_delay': max_delay,
            'deadline': submit_time + duration + max_delay,
            'power_kw': round(power_kw, 2)
        })
        
    df_jobs = pd.DataFrame(jobs).sort_values('submit_time').reset_index(drop=True)
    return df_jobs

if __name__ == '__main__':
    grid_df = generate_grid_carbon_data()
    jobs_df = generate_job_queue()
    print("Grid Carbon Intensity Sample:")
    print(grid_df.head())
    print("\nJob Queue Sample:")
    print(jobs_df.head())
