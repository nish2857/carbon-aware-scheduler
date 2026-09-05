"""
Grid Data Provider for Dynamic Carbon-Aware Cloud Workload Scheduler.
Generates multi-region hourly grid carbon intensity data (gCO2eq/kWh),
energy tariffs ($/kWh), and fuel mix distributions across global cloud regions.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

REGION_METADATA = {
    'US-East-1': {
        'name': 'US East (N. Virginia)',
        'location': 'Virginia, USA',
        'coordinates': {'lat': 39.0438, 'lng': -77.4874},
        'base_carbon': 420.0,
        'base_cost': 0.12,
        'primary_clean': 'Solar & Nuclear',
        'grid_type': 'PJM Interconnection'
    },
    'US-West-2': {
        'name': 'US West (Oregon)',
        'location': 'Oregon, USA',
        'coordinates': {'lat': 45.8399, 'lng': -119.7006},
        'base_carbon': 240.0,
        'base_cost': 0.08,
        'primary_clean': 'Hydro & Solar',
        'grid_type': 'BPA Hydro Grid'
    },
    'EU-Central-1': {
        'name': 'Europe (Frankfurt)',
        'location': 'Frankfurt, Germany',
        'coordinates': {'lat': 50.1109, 'lng': 8.6821},
        'base_carbon': 180.0,
        'base_cost': 0.22,
        'primary_clean': 'Wind & Solar',
        'grid_type': 'ENTSO-E Grid'
    },
    'AP-South-1': {
        'name': 'Asia Pacific (Mumbai)',
        'location': 'Mumbai, India',
        'coordinates': {'lat': 19.0760, 'lng': 72.8777},
        'base_carbon': 580.0,
        'base_cost': 0.10,
        'primary_clean': 'Solar',
        'grid_type': 'WESTERN REGION GRID'
    },
    'SA-East-1': {
        'name': 'South America (São Paulo)',
        'location': 'São Paulo, Brazil',
        'coordinates': {'lat': -23.5505, 'lng': -46.6333},
        'base_carbon': 110.0,
        'base_cost': 0.14,
        'primary_clean': 'Hydroelectric',
        'grid_type': 'SIN Hydro System'
    },
    'AP-Northeast-1': {
        'name': 'Asia Pacific (Tokyo)',
        'location': 'Tokyo, Japan',
        'coordinates': {'lat': 35.6762, 'lng': 139.6503},
        'base_carbon': 390.0,
        'base_cost': 0.18,
        'primary_clean': 'Nuclear & Solar',
        'grid_type': 'TEPCO Grid'
    }
}

class GridDataProvider:
    """Generates synthetic historical and forecast grid carbon intensity data."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.regions = list(REGION_METADATA.keys())

    def generate_timeline_data(self, days: int = 14, start_date: datetime = None) -> pd.DataFrame:
        """
        Generates hourly grid carbon intensity (gCO2eq/kWh) and energy cost ($/kWh)
        over the specified number of days for all cloud regions.
        """
        np.random.seed(self.seed)
        hours = days * 24
        if start_date is None:
            start_date = datetime(2026, 8, 1, 0, 0, 0)

        timestamps = [start_date + timedelta(hours=i) for i in range(hours)]
        time_of_day = np.array([t.hour for t in timestamps])
        days_of_week = np.array([t.weekday() for t in timestamps])

        data = {
            'timestamp': timestamps,
            'hour': time_of_day,
            'day_of_week': days_of_week
        }

        for region, meta in REGION_METADATA.items():
            base_c = meta['base_carbon']
            base_p = meta['base_cost']

            # Regional diurnal characteristics
            if region == 'US-East-1':
                # Solar midday drop + evening demand peak
                solar_effect = -110 * np.sin((time_of_day - 6) * np.pi / 12).clip(0, 1)
                peak_effect = 40 * ((time_of_day >= 17) & (time_of_day <= 21))
                noise = np.random.normal(0, 18, hours)
                carbon = base_c + solar_effect + peak_effect + noise

            elif region == 'US-West-2':
                # Deep afternoon solar dip
                solar_effect = -160 * np.sin((time_of_day - 7) * np.pi / 11).clip(0, 1)
                noise = np.random.normal(0, 15, hours)
                carbon = base_c + solar_effect + noise

            elif region == 'EU-Central-1':
                # High wind fluctuation + solar dip
                wind_fluctuation = 60 * np.sin(np.linspace(0, days * 2 * np.pi, hours))
                solar_effect = -50 * np.sin((time_of_day - 7) * np.pi / 10).clip(0, 1)
                noise = np.random.normal(0, 20, hours)
                carbon = base_c + wind_fluctuation + solar_effect + noise

            elif region == 'AP-South-1':
                # High coal baseline, sharp evening thermal peak
                peak_effect = 90 * ((time_of_day >= 18) & (time_of_day <= 22))
                solar_effect = -70 * np.sin((time_of_day - 6) * np.pi / 12).clip(0, 1)
                noise = np.random.normal(0, 22, hours)
                carbon = base_c + peak_effect + solar_effect + noise

            elif region == 'SA-East-1':
                # Very clean hydro baseline, minor seasonal/diurnal variation
                noise = np.random.normal(0, 12, hours)
                carbon = base_c + 15 * np.sin(time_of_day * np.pi / 12) + noise

            elif region == 'AP-Northeast-1':
                # Gas + Nuclear mix, evening peak demand
                peak_effect = 50 * ((time_of_day >= 18) & (time_of_day <= 21))
                solar_effect = -60 * np.sin((time_of_day - 6) * np.pi / 12).clip(0, 1)
                noise = np.random.normal(0, 16, hours)
                carbon = base_c + peak_effect + solar_effect + noise

            # Dynamic electricity price correlated with peak carbon / demand
            price_multiplier = 1.0 + 0.3 * ((time_of_day >= 16) & (time_of_day <= 21))
            prices = base_p * price_multiplier + np.random.normal(0, 0.005, hours)

            data[f'{region}_carbon'] = np.clip(carbon, 20.0, 900.0)
            data[f'{region}_price'] = np.clip(prices, 0.03, 0.55)

        return pd.DataFrame(data)

    def get_region_fuel_mix(self, region: str, carbon_intensity: float) -> Dict[str, float]:
        """Calculates dynamic percentage mix of energy generation sources based on carbon intensity."""
        if region not in REGION_METADATA:
            raise ValueError(f"Unknown region: {region}")

        # Scale clean vs fossil ratio inversely with carbon intensity
        meta = REGION_METADATA[region]
        base_c = meta['base_carbon']
        ratio = max(0.1, min(1.0, 1.0 - (carbon_intensity - 50.0) / 700.0))

        if region == 'SA-East-1':
            hydro = min(85.0, 60.0 + ratio * 25.0)
            wind = 10.0
            solar = 5.0
            gas = max(0.0, 100.0 - (hydro + wind + solar))
            return {'Hydro': round(hydro, 1), 'Wind': round(wind, 1), 'Solar': round(solar, 1), 'Gas': round(gas, 1), 'Coal': 0.0}

        elif region == 'EU-Central-1':
            clean_pct = min(80.0, 30.0 + ratio * 50.0)
            wind = clean_pct * 0.5
            solar = clean_pct * 0.3
            nuclear = clean_pct * 0.2
            coal_gas = 100.0 - clean_pct
            return {'Wind': round(wind, 1), 'Solar': round(solar, 1), 'Nuclear': round(nuclear, 1), 'Gas': round(coal_gas * 0.6, 1), 'Coal': round(coal_gas * 0.4, 1)}

        elif region == 'US-West-2':
            clean_pct = min(85.0, 40.0 + ratio * 45.0)
            hydro = clean_pct * 0.55
            solar = clean_pct * 0.30
            wind = clean_pct * 0.15
            fossil = 100.0 - clean_pct
            return {'Hydro': round(hydro, 1), 'Solar': round(solar, 1), 'Wind': round(wind, 1), 'Gas': round(fossil, 1), 'Coal': 0.0}

        elif region == 'AP-South-1':
            clean_pct = min(40.0, 10.0 + ratio * 30.0)
            solar = clean_pct * 0.7
            wind = clean_pct * 0.3
            fossil = 100.0 - clean_pct
            return {'Solar': round(solar, 1), 'Wind': round(wind, 1), 'Coal': round(fossil * 0.8, 1), 'Gas': round(fossil * 0.2, 1)}

        else:
            clean_pct = min(70.0, 20.0 + ratio * 50.0)
            solar = clean_pct * 0.4
            nuclear = clean_pct * 0.4
            wind = clean_pct * 0.2
            fossil = 100.0 - clean_pct
            return {'Solar': round(solar, 1), 'Nuclear': round(nuclear, 1), 'Wind': round(wind, 1), 'Gas': round(fossil * 0.6, 1), 'Coal': round(fossil * 0.4, 1)}


if __name__ == '__main__':
    provider = GridDataProvider()
    df = provider.generate_timeline_data(days=2)
    print("Generated Grid Carbon & Tariff Data Sample:")
    print(df[['timestamp', 'US-East-1_carbon', 'US-East-1_price', 'EU-Central-1_carbon', 'EU-Central-1_price']].head())
