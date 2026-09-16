"""
View 1: Incoming Report View.
Displays the current incoming report in file order and the stream of reports processed so far.
Clean, simplified, zero emojis.
"""
import textwrap
import streamlit as st
import pandas as pd
from src.replay_engine import ReplayEngine
from src.models import CampusReport
from src.components.style import (
    get_severity_badge_html,
    get_relationship_badge_html,
    get_incident_badge_html,
)


def render_incoming_report_view(replay_engine: ReplayEngine):
    """Render a clean, minimal Incoming Report View."""
    current_tick = replay_engine.get_current_tick()
    report: CampusReport = current_tick.report
    prediction = current_tick.prediction

    st.markdown("### Incoming Report")

    # 1. Single Clean Card for the Current Report
    card_html = textwrap.dedent(f"""
<div style="background: #111827; border: 1px solid #374151; border-radius: 8px; padding: 1.2rem; margin-bottom: 1.2rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #1F2937; padding-bottom: 10px;">
        <div>
            <span style="color: #818CF8; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">
                Report {replay_engine.current_tick_idx + 1} of {replay_engine.total_ticks}
            </span>
            <h2 style="margin: 2px 0 0 0; color: #FFFFFF; font-size: 1.4rem; font-weight: 700; line-height: 1.35;">
                {report.report_id} &mdash; {report.clean_location}
            </h2>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            {get_severity_badge_html(report.reported_severity)}
            {get_relationship_badge_html(prediction.relationship)}
            {get_incident_badge_html(prediction.incident_id)}
        </div>
    </div>
    <div style="display: flex; gap: 16px; font-size: 0.82rem; color: #9CA3AF; margin-bottom: 10px;">
        <span>Category: <strong style="color:#F3F4F6; text-transform:capitalize;">{report.category or 'Unknown'}</strong></span>
        <span>Reporter: <strong style="color:#F3F4F6; text-transform:capitalize;">{report.reporter_type or 'Anonymous'}</strong></span>
        <span>Timestamp: <strong style="color:#F3F4F6; font-family:'JetBrains Mono', monospace;">{report.timestamp}</strong></span>
    </div>
    <div style="background: #1F2937; border-radius: 6px; padding: 0.9rem 1rem;">
        <div style="font-size: 0.72rem; color: #9CA3AF; text-transform: uppercase; font-weight: 700; letter-spacing: 0.04em; margin-bottom: 3px;">
            Report Evidence Text:
        </div>
        <div style="color: #F9FAFB; font-size: 0.96rem; line-height: 1.45;">
            "{report.description}"
        </div>
    </div>
</div>
""").strip()
    st.markdown(card_html, unsafe_allow_html=True)

    # 2. Simple Table of Processed Reports
    cumulative_reports = replay_engine.get_cumulative_reports()
    st.markdown(f"#### Ingestion Stream ({len(cumulative_reports)} reports processed so far)")

    table_data = []
    for r in reversed(cumulative_reports):
        table_data.append({
            "Report ID": r.report_id,
            "Timestamp": r.timestamp,
            "Location": r.clean_location,
            "Category": r.clean_category,
            "Severity": r.reported_severity,
            "Reporter": r.reporter_type,
            "Description": r.description,
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        column_config={
            "Report ID": st.column_config.TextColumn("Report ID", width="small"),
            "Timestamp": st.column_config.TextColumn("Timestamp", width="small"),
            "Location": st.column_config.TextColumn("Location", width="medium"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Reporter": st.column_config.TextColumn("Reporter", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
        },
        use_container_width=True,
        hide_index=True,
    )
