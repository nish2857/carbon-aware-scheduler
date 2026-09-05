"""
Cloud Job Model and Workload Generator for Carbon-Aware Scheduler.
Models compute resource requirements, power draw, spatial constraints, and SLA deadlines.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

JOB_TYPES = {
    'AI Training': {
        'avg_power_kw': 180.0,
        'avg_duration': 6,
        'avg_delay_sla': 18,
        'spatial_flexible': True,
        'gpus': 16,
        'icon': '🤖'
    },
    'Data Pipeline': {
        'avg_power_kw': 85.0,
        'avg_duration': 3,
        'avg_delay_sla': 8,
        'spatial_flexible': True,
        'gpus': 0,
        'icon': '📊'
    },
    'Video Encoding': {
        'avg_power_kw': 60.0,
        'avg_duration': 2,
        'avg_delay_sla': 12,
        'spatial_flexible': True,
        'gpus': 4,
        'icon': '🎬'
    },
    'Database Backup': {
        'avg_power_kw': 35.0,
        'avg_duration': 4,
        'avg_delay_sla': 6,
        'spatial_flexible': False,
        'gpus': 0,
        'icon': '💾'
    },
    'Genomics Pipeline': {
        'avg_power_kw': 140.0,
        'avg_duration': 8,
        'avg_delay_sla': 24,
        'spatial_flexible': True,
        'gpus': 8,
        'icon': '🧬'
    }
}

@dataclass
class CloudJob:
    """Represents an individual cloud compute workload task."""
    job_id: str
    job_type: str
    submit_time: int
    duration: int
    power_kw: float
    max_delay: int
    deadline: int
    priority: str = 'Medium'
    cpu_cores: int = 32
    ram_gb: int = 128
    gpus: int = 0
    allowed_regions: List[str] = field(default_factory=lambda: ['US-East-1', 'US-West-2', 'EU-Central-1', 'AP-South-1', 'SA-East-1', 'AP-Northeast-1'])

    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'submit_time': self.submit_time,
            'duration': self.duration,
            'power_kw': self.power_kw,
            'max_delay': self.max_delay,
            'deadline': self.deadline,
            'priority': self.priority,
            'cpu_cores': self.cpu_cores,
            'ram_gb': self.ram_gb,
            'gpus': self.gpus,
            'allowed_regions': self.allowed_regions
        }


class JobGenerator:
    """Generates realistic batch workload queues for scheduler benchmarking."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def generate_workload_queue(self, num_jobs: int = 100, simulation_hours: int = 48) -> List[CloudJob]:
        """Generates a queue of cloud workloads across simulation timeframe."""
        np.random.seed(self.seed)
        all_regions = ['US-East-1', 'US-West-2', 'EU-Central-1', 'AP-South-1', 'SA-East-1', 'AP-Northeast-1']
        job_type_names = list(JOB_TYPES.keys())
        priorities = ['Low', 'Medium', 'High', 'Critical']
        priority_weights = [0.2, 0.5, 0.2, 0.1]

        jobs: List[CloudJob] = []

        for i in range(1, num_jobs + 1):
            jtype = np.random.choice(job_type_names, p=[0.25, 0.30, 0.20, 0.15, 0.10])
            specs = JOB_TYPES[jtype]

            # Submit time distributed across simulation window
            submit_t = int(np.random.randint(0, max(1, simulation_hours - 14)))
            
            # Duration & SLA variation
            duration = max(1, int(np.random.normal(specs['avg_duration'], 1.2)))
            max_delay = max(0, int(np.random.normal(specs['avg_delay_sla'], 3.0)))
            power_kw = round(float(np.random.normal(specs['avg_power_kw'], 15.0)), 2)

            priority = str(np.random.choice(priorities, p=priority_weights))
            if priority == 'Critical':
                max_delay = min(max_delay, 2) # Strict SLA for critical jobs

            # Spatial flexibility
            if specs['spatial_flexible']:
                # Random subset of 3-6 allowed regions
                n_allowed = np.random.randint(3, len(all_regions) + 1)
                allowed = list(np.random.choice(all_regions, size=n_allowed, replace=False))
            else:
                # Locked to default home region
                allowed = ['US-East-1']

            deadline = submit_t + duration + max_delay

            job = CloudJob(
                job_id=f"JOB-{i:03d}",
                job_type=jtype,
                submit_time=submit_t,
                duration=duration,
                power_kw=max(10.0, power_kw),
                max_delay=max_delay,
                deadline=deadline,
                priority=priority,
                cpu_cores=int(power_kw * 0.4),
                ram_gb=int(power_kw * 1.5),
                gpus=specs['gpus'],
                allowed_regions=allowed
            )
            jobs.append(job)

        jobs.sort(key=lambda j: j.submit_time)
        return jobs

    def to_dataframe(self, jobs: List[CloudJob]) -> pd.DataFrame:
        """Converts job list to Pandas DataFrame."""
        return pd.DataFrame([j.to_dict() for j in jobs])


if __name__ == '__main__':
    gen = JobGenerator()
    jobs = gen.generate_workload_queue(num_jobs=10)
    print("Generated 10 Cloud Jobs Sample:")
    for j in jobs:
        print(j.to_dict())
