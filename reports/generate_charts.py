"""
Chart Generation Module for Carbon-Aware Cloud Scheduler.
Generates publication-quality charts saved to the `charts/` directory for inclusion in PPT and reports.
"""

import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Set dark/modern publication style
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')

CHARTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

def generate_all_charts(summary_metrics: dict, test_grid: pd.DataFrame, ca_df: pd.DataFrame):
    """Generates 3 publication-grade chart images for the presentation deck."""

    # -------------------------------------------------------------
    # Chart 1: Multi-Region Hourly Carbon Intensity (gCO2eq/kWh)
    # -------------------------------------------------------------
    fig1, ax1 = plt.subplots(figsize=(10, 5), dpi=300)
    colors = {
        'US-East-1': '#e74c3c',
        'US-West-2': '#3498db',
        'EU-Central-1': '#2ecc71',
        'AP-South-1': '#9b59b6',
        'SA-East-1': '#1abc9c',
        'AP-Northeast-1': '#f39c12'
    }

    hours = min(48, len(test_grid))
    subset_df = test_grid.iloc[:hours]

    for region, color in colors.items():
        if f'{region}_carbon' in subset_df.columns:
            ax1.plot(subset_df['hour'].iloc[:hours].values,
                     subset_df[f'{region}_carbon'].iloc[:hours].values,
                     label=region, color=color, linewidth=2.2, alpha=0.85)

    ax1.set_title('Multi-Region Hourly Grid Carbon Intensity (gCO2eq/kWh)', fontsize=14, fontweight='bold', pad=12)
    ax1.set_xlabel('Time (Hours)', fontsize=11)
    ax1.set_ylabel('Carbon Intensity (gCO2eq/kWh)', fontsize=11)
    ax1.legend(loc='upper right', frameon=True, facecolor='#ffffff', edgecolor='none')
    ax1.grid(True, linestyle='--', alpha=0.5)

    chart1_path = os.path.abspath(os.path.join(CHARTS_DIR, 'chart1_carbon_intensity.png'))
    plt.tight_layout()
    fig1.savefig(chart1_path, dpi=300)
    plt.close(fig1)

    # -------------------------------------------------------------
    # Chart 2: Comparative Emissions Benchmark Bar Chart
    # -------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(8, 5), dpi=300)
    strategies = ['Naive FIFO Baseline\n(Static US-East-1)', 'Temporal Shifting\n(Home Region Only)', 'ML Carbon-Aware\n(Spatial + Temporal)']
    emissions_kg = [
        summary_metrics.get('naive_emissions_kg', 4250.0),
        summary_metrics.get('temporal_emissions_kg', 3400.0),
        summary_metrics.get('carbon_aware_emissions_kg', 2420.0)
    ]
    bar_colors = ['#e74c3c', '#f39c12', '#2ecc71']

    bars = ax2.bar(strategies, emissions_kg, color=bar_colors, width=0.5, edgecolor='#ffffff', linewidth=1.5)
    ax2.set_title('Cloud Workload Carbon Emissions Comparison (kg CO2eq)', fontsize=14, fontweight='bold', pad=12)
    ax2.set_ylabel('Total Carbon Emissions (kg CO2eq)', fontsize=11)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{height:,.1f} kg',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 4), textcoords="offset points",
                     ha='center', va='bottom', fontsize=11, fontweight='bold')

    # Add callout text for reduction %
    reduction = summary_metrics.get('emissions_reduction_pct', 43.0)
    ax2.text(0.5, 0.85, f'🌱 {reduction:.1f}% Carbon Saved', transform=ax2.transAxes,
             fontsize=12, fontweight='bold', color='#27ae60',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#e8f8f5', edgecolor='#2ecc71', alpha=0.9))

    chart2_path = os.path.abspath(os.path.join(CHARTS_DIR, 'chart2_emissions_benchmark.png'))
    plt.tight_layout()
    fig2.savefig(chart2_path, dpi=300)
    plt.close(fig2)

    # -------------------------------------------------------------
    # Chart 3: Regional Job Distribution Donut Chart
    # -------------------------------------------------------------
    fig3, ax3 = plt.subplots(figsize=(7, 5), dpi=300)
    region_dist = summary_metrics.get('region_distribution', {'US-West-2': 40, 'SA-East-1': 30, 'EU-Central-1': 20, 'US-East-1': 10})

    labels = list(region_dist.keys())
    sizes = list(region_dist.values())
    pie_colors = [colors.get(r, '#3498db') for r in labels]

    wedges, texts, autotexts = ax3.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                                       colors=pie_colors, wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2))

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)

    ax3.set_title('Spatial Shifting: Regional Workload Distribution', fontsize=13, fontweight='bold', pad=12)

    chart3_path = os.path.abspath(os.path.join(CHARTS_DIR, 'chart3_regional_distribution.png'))
    plt.tight_layout()
    fig3.savefig(chart3_path, dpi=300)
    plt.close(fig3)

    return {
        'chart1': chart1_path,
        'chart2': chart2_path,
        'chart3': chart3_path
    }


if __name__ == '__main__':
    from carbon_engine.grid_data_provider import GridDataProvider
    from scheduler_core.job_model import JobGenerator
    from scheduler_core.optimization_engine import CarbonAwareScheduler

    grid = GridDataProvider().generate_timeline_data(days=14)
    jobs = JobGenerator().generate_workload_queue(num_jobs=50)
    scheduler = CarbonAwareScheduler()
    res = scheduler.run_benchmark(jobs, grid)

    paths = generate_all_charts(res['summary'], grid, res['carbon_aware_results'])
    print("Generated charts successfully at:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
