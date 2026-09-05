"""
Chart Generator for Dynamic Carbon-Aware Cloud Workload Scheduler.
Saves PNG charts for presentation slides and documentation.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from data_generator import generate_grid_carbon_data, generate_job_queue
from ml_scheduler import run_scheduler_simulation

def generate_all_charts(output_dir='charts'):
    os.makedirs(output_dir, exist_ok=True)
    
    # Set styling
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams.update({
        'font.sans-serif': 'DejaVu Sans',
        'font.family': 'sans-serif',
        'figure.dpi': 300,
        'axes.labelsize': 11,
        'axes.titlesize': 13,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 10
    })
    
    grid = generate_grid_carbon_data()
    jobs = generate_job_queue()
    metrics, naive_df, ca_df, test_grid = run_scheduler_simulation(grid, jobs)
    
    # Chart 1: Multi-Region Carbon Intensity Profile
    fig, ax = plt.subplots(figsize=(10, 4.5))
    hours_to_plot = 72 # 3 days
    subset = test_grid.iloc[:hours_to_plot]
    
    colors = {'US-East': '#e74c3c', 'US-West': '#f39c12', 'EU-Central': '#2ecc71', 'AP-South': '#9b59b6'}
    for r in ['US-East', 'US-West', 'EU-Central', 'AP-South']:
        ax.plot(subset.index, subset[r], label=r, color=colors[r], linewidth=2)
        
    ax.set_title('Multi-Region Grid Carbon Intensity Dynamics (gCO2eq/kWh)', pad=12, weight='bold')
    ax.set_xlabel('Simulation Hour')
    ax.set_ylabel('Carbon Intensity (gCO2eq/kWh)')
    ax.legend(loc='upper right', frameon=True)
    ax.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    chart1_path = os.path.join(output_dir, 'chart1_carbon_intensity.png')
    plt.savefig(chart1_path)
    plt.close()
    
    # Chart 2: Total Carbon Emissions Comparison (Naive vs Carbon-Aware)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    categories = ['Naive Baseline\n(US-East Static)', 'ML Carbon-Aware\n(Spatial + Temporal)']
    emissions = [metrics['naive_emissions_kg'], metrics['carbon_aware_emissions_kg']]
    bar_colors = ['#e74c3c', '#27ae60']
    
    bars = ax.bar(categories, emissions, color=bar_colors, width=0.5, edgecolor='black', linewidth=1.2)
    ax.set_ylabel('Total Emissions (kg CO2eq)', weight='bold')
    ax.set_title('Carbon Reduction Impact Benchmark', pad=14, weight='bold')
    
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f} kg',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, weight='bold')
                    
    # Add reduction badge text
    reduction_pct = metrics['reduction_percentage']
    ax.text(0.5, 0.85, f'▼ {reduction_pct}% Carbon Saved', 
            transform=ax.transAxes, ha='center', fontsize=12, weight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#e8f8f5', edgecolor='#27ae60', linewidth=2))
            
    ax.set_ylim(0, max(emissions) * 1.25)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    chart2_path = os.path.join(output_dir, 'chart2_emissions_benchmark.png')
    plt.savefig(chart2_path)
    plt.close()
    
    # Chart 3: Regional Load Allocation Breakdown
    fig, ax = plt.subplots(figsize=(7, 4.5))
    region_dist = metrics['region_distribution']
    regions_list = list(region_dist.keys())
    job_counts = [region_dist[r] for r in regions_list]
    pie_colors = [colors[r] for r in regions_list]
    
    wedges, texts, autotexts = ax.pie(job_counts, labels=regions_list, autopct='%1.1f%%',
                                      startangle=140, colors=pie_colors,
                                      wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2))
                                      
    plt.setp(autotexts, size=10, weight="bold", color="white")
    ax.set_title('ML Scheduler Regional Job Migration Distribution', pad=12, weight='bold')
    plt.tight_layout()
    chart3_path = os.path.join(output_dir, 'chart3_regional_distribution.png')
    plt.savefig(chart3_path)
    plt.close()
    
    print(f"All charts successfully generated in '{output_dir}/':")
    print(f"- {chart1_path}")
    print(f"- {chart2_path}")
    print(f"- {chart3_path}")
    
    return {
        'chart1': chart1_path,
        'chart2': chart2_path,
        'chart3': chart3_path
    }

if __name__ == '__main__':
    generate_all_charts()
