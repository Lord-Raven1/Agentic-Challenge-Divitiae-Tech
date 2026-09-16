"""
View 3: Incident Summary View.
Displays: current type, location, severity, confidence, reports, services, status, and action for every incident.
Clicking/selecting an incident reveals its reports and current assessment.
Zero emojis, clean layout.
"""
import textwrap
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.replay_engine import ReplayEngine
from src.models import IncidentSnapshot
from src.components.style import (
    get_severity_badge_html,
    get_status_badge_html,
)


def render_incident_summary_view(replay_engine: ReplayEngine):
    """Render a clean, simplified Incident Summary View."""
    incidents = replay_engine.get_incident_states()
    current_tick = replay_engine.get_current_tick()

    st.markdown("### Incident Summary")
    st.caption("Evolving incident clusters tracked across campus.")

    if not incidents:
        st.info("No incidents tracked yet.")
        return

    # 1. Incident Registry Table with the 8 EXACT Required Columns:
    # current type, location, severity, confidence, reports, services, status and action
    table_rows = []
    for inc_id, inc in incidents.items():
        table_rows.append({
            "Incident ID": inc.incident_id,
            "Current Type": inc.current_type.capitalize(),
            "Location": inc.location,
            "Severity": inc.severity,
            "Confidence": f"{inc.confidence * 100:.0f}%",
            "Reports Count": inc.reports_count,
            "Reports": ", ".join(inc.report_ids),
            "Services": ", ".join(inc.services) if inc.services else "None",
            "Status": inc.status,
            "Action": inc.action,
        })

    df_incidents = pd.DataFrame(table_rows)
    st.dataframe(
        df_incidents,
        column_config={
            "Incident ID": st.column_config.TextColumn("Incident ID", width="small"),
            "Current Type": st.column_config.TextColumn("Type", width="small"),
            "Location": st.column_config.TextColumn("Location", width="medium"),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Confidence": st.column_config.TextColumn("Confidence", width="small"),
            "Reports Count": st.column_config.NumberColumn("Reports", width="small"),
            "Reports": st.column_config.TextColumn("Report IDs", width="medium"),
            "Services": st.column_config.TextColumn("Services Dispatched", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Action": st.column_config.TextColumn("Action", width="medium"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # 2. Interactive Incident Drilldown (Checklist item: "Clicking an incident reveals its reports and current assessment")
    st.markdown("---")
    st.markdown("#### Incident Evidence & Current Assessment")

    default_selected = current_tick.active_incident_id if current_tick.active_incident_id in incidents else list(incidents.keys())[0]
    
    incident_options = list(incidents.keys())
    selected_incident_id = st.selectbox(
        "Select Incident to Inspect:",
        options=incident_options,
        index=incident_options.index(default_selected) if default_selected in incident_options else 0,
        format_func=lambda x: f"{x} - {incidents[x].location} ({incidents[x].current_type.capitalize()}) | Status: {incidents[x].status} | {incidents[x].reports_count} reports",
        key="selected_incident_clean",
    )

    sel_inc: IncidentSnapshot = incidents[selected_incident_id]

    col_details, col_visual = st.columns([6, 5])

    with col_details:
        card_html = textwrap.dedent(f"""
<div style="background:#111827; border:1px solid #374151; border-radius:8px; padding:1.1rem; margin-bottom:1rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <h3 style="margin:0; color:#FFFFFF; font-size:1.25rem;">Incident {sel_inc.incident_id}: {sel_inc.location}</h3>
        <div style="display:flex; align-items:center; gap:8px;">
            {get_severity_badge_html(sel_inc.severity)}
            {get_status_badge_html(sel_inc.status)}
        </div>
    </div>
    <div style="font-size:0.83rem; color:#9CA3AF; margin-bottom:10px;">
        Type: <strong style="color:#F3F4F6;">{sel_inc.current_type.capitalize()}</strong> &nbsp;|&nbsp; 
        Confidence: <strong style="color:#10B981;">{sel_inc.confidence * 100:.0f}%</strong> &nbsp;|&nbsp; 
        Services: <strong style="color:#F3F4F6;">{', '.join(sel_inc.services) if sel_inc.services else 'None'}</strong>
    </div>
    <div style="background:#1F2937; border-radius:6px; padding:0.8rem 1rem;">
        <div style="font-size:0.75rem; color:#9CA3AF; text-transform:uppercase; font-weight:600; margin-bottom:3px;">
            Current Assessment:
        </div>
        <div style="color:#F9FAFB; font-size:0.88rem; line-height:1.4;">
            {sel_inc.evolving_assessment}
        </div>
    </div>
</div>
""").strip()
        st.markdown(card_html, unsafe_allow_html=True)

        st.markdown(f"**Linked Reports ({len(sel_inc.reports_history)} received)**")
        for rep in sel_inc.reports_history:
            rep_html = textwrap.dedent(f"""
<div style="background:#1F2937; border-left:3px solid #6366F1; border-radius:0 4px 4px 0; padding:6px 10px; margin-bottom:5px; font-size:0.82rem;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <strong style="color:#818CF8;">Report {rep.report_id}</strong>
        <span style="color:#9CA3AF; font-family:'JetBrains Mono', monospace;">{rep.timestamp}</span>
    </div>
    <div style="color:#E5E7EB; margin:2px 0;">"{rep.description}"</div>
    <div style="color:#9CA3AF; font-size:0.75rem;">Source: {rep.reporter_type} | Reported: {rep.reported_severity}</div>
</div>
""").strip()
            st.markdown(rep_html, unsafe_allow_html=True)

    with col_visual:
        st.markdown("**Confidence Progression**")
        if sel_inc.confidence_progression:
            x_vals = [f"R{idx+1}" for idx in range(len(sel_inc.confidence_progression))]
            y_conf = [c * 100 for c in sel_inc.confidence_progression]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_conf,
                mode="lines+markers",
                line=dict(color="#6366F1", width=2),
                marker=dict(size=6, color="#818CF8"),
            ))
            
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17, 24, 39, 0.6)",
                font=dict(family="Inter", size=10, color="#9CA3AF"),
                height=220,
                margin=dict(l=30, r=20, t=10, b=30),
                yaxis=dict(range=[30, 100], title="% Conf"),
            )
            st.plotly_chart(fig, use_container_width=True)
