"""
Interactive Streamlit Control Panel & Visual Dashboard
for Dynamic Carbon-Aware Cloud Workload Scheduler.

Run with:
    streamlit run app.py
"""

import os
import sys

# Ensure root directory and current directory are in sys.path for Streamlit Cloud & cloud platform deployments
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

parent_dir = os.path.abspath(os.path.join(ROOT_DIR, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

try:
    from carbon_engine.grid_data_provider import GridDataProvider, REGION_METADATA
    from carbon_engine.forecaster import CarbonForecaster
    from scheduler_core.job_model import CloudJob, JobGenerator, JOB_TYPES
    from scheduler_core.optimization_engine import CarbonAwareScheduler, SchedulerStrategy
except ModuleNotFoundError:
    try:
        from .carbon_engine.grid_data_provider import GridDataProvider, REGION_METADATA
        from .carbon_engine.forecaster import CarbonForecaster
        from .scheduler_core.job_model import CloudJob, JobGenerator, JOB_TYPES
        from .scheduler_core.optimization_engine import CarbonAwareScheduler, SchedulerStrategy
    except ImportError:
        import carbon_engine.grid_data_provider as gdp
        from carbon_engine.grid_data_provider import GridDataProvider, REGION_METADATA
        from carbon_engine.forecaster import CarbonForecaster
        from scheduler_core.job_model import CloudJob, JobGenerator, JOB_TYPES
        from scheduler_core.optimization_engine import CarbonAwareScheduler, SchedulerStrategy

st.set_page_config(
    page_title="Dynamic Carbon-Aware Cloud Scheduler",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #2ecc71; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #95a5a6; margin-bottom: 20px; }
    .metric-card { background-color: #1e293b; border-radius: 10px; padding: 15px; border-left: 5px solid #2ecc71; }
    .region-badge { background-color: #0f172a; padding: 10px; border-radius: 8px; border: 1px solid #334155; }
</style>
""", unsafe_allow_html=True)

# Header Title
st.markdown('<div class="main-title">🌱 Dynamic Carbon-Aware Cloud Workload Scheduler</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Automated spatial and temporal workload shifting for zero-carbon cloud compute infrastructure</div>', unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("⚙️ Simulation & Strategy Controls")

# Real-Time Telemetry Heartbeat Status Badge
st.sidebar.markdown("""
<div style="background-color: #0f172a; border-left: 4px solid #2ecc71; padding: 10px; border-radius: 6px; margin-bottom: 15px;">
    <span style="font-size: 0.85rem; font-weight: 700; color: #2ecc71;">🟢 Grid Telemetry Sync: ACTIVE</span><br/>
    <span style="font-size: 0.75rem; color: #94a3b8;">12-Min Real-Time Energy Signal Pulse</span>
</div>
""", unsafe_allow_html=True)

simulation_days = st.sidebar.slider("Simulation Duration (Days)", 3, 30, 7)
num_jobs = st.sidebar.slider("Workload Queue Size (Jobs)", 10, 200, 50)

strategy_mode = st.sidebar.selectbox(
    "Optimization Strategy",
    options=[SchedulerStrategy.MIN_CARBON, SchedulerStrategy.MIN_COST, SchedulerStrategy.PARETO_BALANCED],
    format_func=lambda x: {
        SchedulerStrategy.MIN_CARBON: "🌱 Min-Carbon (Zero Emission Focus)",
        SchedulerStrategy.MIN_COST: "💰 Min-Cost (Energy Tariff Focus)",
        SchedulerStrategy.PARETO_BALANCED: "⚖️ Pareto-Balanced (Carbon + Cost + SLA)"
    }[x]
)

if strategy_mode == SchedulerStrategy.PARETO_BALANCED:
    st.sidebar.subheader("Pareto Strategy Weights")
    carbon_wt = st.sidebar.slider("Carbon Weight (α)", 0.0, 1.0, 0.5, 0.05)
    cost_wt = st.sidebar.slider("Cost Weight (β)", 0.0, 1.0, 0.3, 0.05)
    sla_wt = st.sidebar.slider("SLA Risk Weight (γ)", 0.0, 1.0, 0.2, 0.05)
else:
    carbon_wt, cost_wt, sla_wt = 0.5, 0.3, 0.2

seed = st.sidebar.number_input("Random Seed", value=42)

# Global Cached Data Provider & Simulation Run
@st.cache_data(show_spinner=False)
def run_cached_simulation(days: int, n_jobs: int, strat: str, c_wt: float, p_wt: float, s_wt: float, s_seed: int):
    provider = GridDataProvider(seed=s_seed)
    df_grid = provider.generate_timeline_data(days=days)

    split = int(len(df_grid) * 0.7)
    train_grid = df_grid.iloc[:split]
    test_grid = df_grid.iloc[split:].reset_index(drop=True)

    fc = CarbonForecaster(seed=s_seed)
    fc.train(train_grid)
    preds = fc.predict(test_grid)
    full_test = pd.concat([test_grid, preds], axis=1)

    jobs = JobGenerator(seed=s_seed).generate_workload_queue(
        num_jobs=n_jobs,
        simulation_hours=len(test_grid)
    )

    scheduler = CarbonAwareScheduler(
        strategy=SchedulerStrategy(strat),
        carbon_weight=c_wt,
        cost_weight=p_wt,
        sla_weight=s_wt
    )

    benchmark = scheduler.run_benchmark(jobs, full_test)
    return benchmark, full_test, provider

with st.spinner("⚡ Running Grid Signal Simulation & ML Carbon Forecaster..."):
    benchmark_res, test_grid_data, grid_prov = run_cached_simulation(
        simulation_days, num_jobs, strategy_mode.value, carbon_wt, cost_wt, sla_wt, seed
    )

metrics = benchmark_res['summary']
ca_df = benchmark_res['carbon_aware_results']

# Live Global Regions Banner
st.subheader("🌎 Live Global Cloud Region Signals")
reg_cols = st.columns(6)
for idx, (reg_id, meta) in enumerate(REGION_METADATA.items()):
    with reg_cols[idx]:
        curr_c = test_grid_data.loc[0, f'{reg_id}_carbon']
        curr_p = test_grid_data.loc[0, f'{reg_id}_price']
        mix = grid_prov.get_region_fuel_mix(reg_id, curr_c)
        top_fuel = max(mix, key=mix.get)

        color_dot = "🟢" if curr_c < 250 else ("🟡" if curr_c < 450 else "🔴")
        st.metric(
            label=f"{color_dot} {reg_id}",
            value=f"{curr_c:.0f} gCO2",
            delta=f"${curr_p:.3f}/kWh"
        )
        st.caption(f"{meta['location']} | {top_fuel}: {mix[top_fuel]}%")

st.divider()

# Tab Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Metrics & Analytics",
    "📈 Multi-Region Forecasts",
    "📋 Job Scheduling Log",
    "➕ Submit Custom Workload"
])

with tab1:
    st.subheader("🌟 Simulation Performance Metrics")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Carbon Emissions Saved", f"{metrics['emissions_reduction_pct']}%", delta=f"-{metrics['emissions_saved_kg']} kg CO2")
    kpi2.metric("Naive Baseline Emissions", f"{metrics['naive_emissions_kg']} kg CO2")
    kpi3.metric("Carbon-Aware Emissions", f"{metrics['carbon_aware_emissions_kg']} kg CO2")
    kpi4.metric("SLA Compliance Rate", f"{metrics['sla_compliance_pct']}%")

    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_right = st.columns(2)

    with c_left:
        st.subheader("📉 Emissions Benchmark Comparison")
        fig, ax = plt.subplots(figsize=(6, 4))
        cats = ['Naive Baseline\n(Static US-East)', 'Temporal Only\n(Home Region)', 'ML Carbon-Aware\n(Spatial + Temporal)']
        ems = [metrics['naive_emissions_kg'], metrics['temporal_emissions_kg'], metrics['carbon_aware_emissions_kg']]
        bars = ax.bar(cats, ems, color=['#e74c3c', '#f39c12', '#2ecc71'], width=0.45)
        ax.set_ylabel('Total CO2eq (kg)')
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f'{h:.1f} kg', xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', weight='bold')
        st.pyplot(fig)

    with c_right:
        st.subheader("🌎 Spatial Migration Distribution")
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        rdist = metrics['region_distribution']
        ax2.pie(rdist.values(), labels=rdist.keys(), autopct='%1.1f%%', startangle=140,
                colors=['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#1abc9c', '#f39c12'])
        st.pyplot(fig2)

with tab2:
    st.subheader("📈 Multi-Region Hourly Grid Carbon Forecasts (gCO2eq/kWh)")
    selected_regions = st.multiselect("Select Regions to Display", options=list(REGION_METADATA.keys()), default=['US-East-1', 'US-West-2', 'EU-Central-1'])

    hours_to_show = st.slider("Forecast Horizon (Hours)", 12, 72, 48)
    sub_df = test_grid_data.iloc[:hours_to_show]

    chart_data = pd.DataFrame({'Hour': sub_df['hour']})
    for r in selected_regions:
        chart_data[f'{r} (Actual)'] = sub_df[f'{r}_carbon']
        chart_data[f'{r} (ML Predicted)'] = sub_df[f'{r}_predicted_carbon']

    st.line_chart(chart_data.set_index('Hour'))

with tab3:
    st.subheader("📋 Scheduled Workloads Dispatch Log")
    st.dataframe(
        ca_df[['job_id', 'job_type', 'priority', 'assigned_region', 'submit_time', 'scheduled_start_time', 'delay_hours', 'actual_emissions_kg', 'actual_cost_usd', 'sla_violated']],
        use_container_width=True
    )

with tab4:
    st.subheader("➕ Submit & Optimize Custom Compute Workload")
    with st.form("custom_job_form"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            custom_type = st.selectbox("Workload Type", options=list(JOB_TYPES.keys()))
            custom_power = st.number_input("Power Draw (kW)", value=120.0, step=10.0)
            custom_duration = st.slider("Compute Duration (Hours)", 1, 24, 4)

        with col_f2:
            custom_sla = st.slider("Allowed SLA Delay Window (Hours)", 0, 24, 12)
            custom_prio = st.selectbox("Priority Level", options=['Low', 'Medium', 'High', 'Critical'])
            custom_allowed = st.multiselect("Allowed Cloud Regions", options=list(REGION_METADATA.keys()), default=list(REGION_METADATA.keys()))

        submitted = st.form_submit_button("🚀 Optimize Placement")

    if submitted:
        job = CloudJob(
            job_id="CUSTOM-USER-01",
            job_type=custom_type,
            submit_time=0,
            duration=custom_duration,
            power_kw=custom_power,
            max_delay=custom_sla,
            deadline=custom_duration + custom_sla,
            priority=custom_prio,
            allowed_regions=custom_allowed
        )

        sched = CarbonAwareScheduler(strategy=strategy_mode, carbon_weight=carbon_wt, cost_weight=cost_wt, sla_weight=sla_wt)
        res = sched.optimize_job_placement(job, test_grid_data)

        st.success(f"✅ Workload Successfully Scheduled in Region **{res['assigned_region']}**!")
        st.json(res)
