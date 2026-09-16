"""
Top KPI Metrics Strip Component for Campus Crisis Agent.
Displays essential, clean operational indicators with zero emojis.
"""
import textwrap
import streamlit as st
from src.replay_engine import ReplayEngine
from src.components.style import (
    get_severity_badge_html,
    get_relationship_badge_html,
)


def render_metrics_bar(replay_engine: ReplayEngine):
    """Render a clean 4-card metric strip for quick situational awareness."""
    current_tick = replay_engine.get_current_tick()
    report = current_tick.report
    prediction = current_tick.prediction
    incidents = replay_engine.get_incident_states()
    
    total_processed = replay_engine.current_tick_idx + 1
    total_in_scenario = replay_engine.total_ticks
    
    # Calculate all dispatched services
    all_services = set()
    for inc in incidents.values():
        all_services.update(inc.services)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Current Report</div>
    <div class="metric-val" style="font-size:1.4rem;">{report.report_id}</div>
    <div class="metric-sub">{total_processed} of {total_in_scenario} processed</div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Incident Cluster</div>
    <div class="metric-val" style="font-size:1.4rem; color:#818CF8;">{prediction.incident_id}</div>
    <div class="metric-sub">{get_relationship_badge_html(prediction.relationship)}</div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Assessed Severity</div>
    <div class="metric-val" style="font-size:1.2rem; margin-top:2px;">
        {get_severity_badge_html(prediction.severity)}
    </div>
    <div class="metric-sub">Confidence: <strong>{prediction.confidence * 100:.0f}%</strong></div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Active Incidents</div>
    <div class="metric-val">{len(incidents)}</div>
    <div class="metric-sub">{len(all_services)} Dispatched Services</div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )
