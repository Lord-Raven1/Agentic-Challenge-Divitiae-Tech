"""
View 2: Decision Log View.
Clean, simplified deliberation log displaying the 9 required fields:
report ID, incident ID, relationship, severity, confidence, decision, service, status, concise reason.
Zero emojis, high clarity.
"""
import textwrap
import streamlit as st
import pandas as pd
from src.replay_engine import ReplayEngine
from src.models import DecisionLogEntry
from src.components.style import (
    get_severity_badge_html,
    get_relationship_badge_html,
    get_human_review_badge_html,
)


def render_decision_log_view(replay_engine: ReplayEngine):
    """Render a clean, simplified Decision Log View."""
    decisions = replay_engine.get_cumulative_decisions()
    current_tick = replay_engine.get_current_tick()
    cur_dec = current_tick.decision

    st.markdown("### Decision Log")
    st.caption("Step-by-step reasoning log for each incoming report.")

    # 1. Simplified Filter Controls
    col_f1, col_f2, col_f3 = st.columns([3, 3, 4])
    with col_f1:
        st.markdown("<div style='padding-top: 7px;'>", unsafe_allow_html=True)
        show_conflicts = st.checkbox(
            f"Conflicting Evidence Only ({len(replay_engine.get_conflict_decisions())})",
            value=False,
            key="chk_conflicts_clean",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col_f2:
        st.markdown("<div style='padding-top: 7px;'>", unsafe_allow_html=True)
        show_human_review = st.checkbox(
            f"Human Review Required ({len(replay_engine.get_human_review_decisions())})",
            value=False,
            key="chk_review_clean",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col_f3:
        all_inc_ids = ["All Incidents"] + sorted(list(set(d.incident_id for d in decisions)))
        selected_inc = st.selectbox(
            "Filter by Incident ID",
            options=all_inc_ids,
            key="sel_inc_clean",
            label_visibility="collapsed",
        )

    # Apply filters
    filtered_decisions = decisions
    if show_conflicts:
        filtered_decisions = [d for d in filtered_decisions if d.conflict_detected or d.relationship == "CONFLICT"]
    if show_human_review:
        filtered_decisions = [d for d in filtered_decisions if d.human_review]
    if selected_inc != "All Incidents":
        filtered_decisions = [d for d in filtered_decisions if d.incident_id == selected_inc]

    st.markdown(f"**Showing {len(filtered_decisions)} of {len(decisions)} decisions**")

    # 2. Main Decision Log Table with the 9 EXACT Required Columns
    if not filtered_decisions:
        st.info("No decisions match the current filter.")
        return

    table_data = []
    for d in reversed(filtered_decisions):
        table_data.append({
            "Report ID": d.report_id,
            "Incident ID": d.incident_id,
            "Relationship": d.relationship,
            "Severity": d.severity,
            "Confidence": f"{d.confidence * 100:.0f}%",
            "Decision": d.decision,
            "Service": d.service,
            "Status": d.status,
            "Concise Reason": d.concise_reason,
            "Human Review": "YES" if d.human_review else "NO",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        column_config={
            "Report ID": st.column_config.TextColumn("Report ID", width="small"),
            "Incident ID": st.column_config.TextColumn("Incident ID", width="small"),
            "Relationship": st.column_config.TextColumn("Relationship", width="small"),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Confidence": st.column_config.TextColumn("Confidence", width="small"),
            "Decision": st.column_config.TextColumn("Decision", width="medium"),
            "Service": st.column_config.TextColumn("Service", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Concise Reason": st.column_config.TextColumn("Concise Reason", width="large"),
            "Human Review": st.column_config.TextColumn("Review", width="small"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # 3. Latest Decision Breakdown
    st.markdown("---")
    st.markdown("#### Latest Agent Deliberation")
    st.markdown(
        textwrap.dedent(f"""
<div style="background:#111827; border:1px solid #374151; border-radius:8px; padding:1rem; font-size:0.88rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid #1F2937; padding-bottom:8px;">
        <span style="font-size:0.95rem; font-weight:700; color:#F9FAFB;">Report {cur_dec.report_id} &rarr; Incident {cur_dec.incident_id}</span>
        <div style="display:flex; align-items:center; gap:8px;">
            {get_severity_badge_html(cur_dec.severity)}
            {get_relationship_badge_html(cur_dec.relationship)}
        </div>
    </div>
    <div style="color:#9CA3AF; margin-bottom:8px;">
        Decision: <strong style="color:#F3F4F6;">{cur_dec.decision}</strong> &nbsp;|&nbsp; 
        Service: <strong style="color:#F3F4F6;">{cur_dec.service}</strong> &nbsp;|&nbsp; 
        Confidence: <strong style="color:#10B981;">{cur_dec.confidence * 100:.0f}%</strong> &nbsp;|&nbsp; 
        Status: <strong style="color:#F3F4F6;">{cur_dec.status}</strong>
    </div>
    <div style="background:#1F2937; padding:8px 12px; border-radius:6px; color:#F3F4F6;">
        <strong>Reason:</strong> {cur_dec.concise_reason}
    </div>
</div>
""").strip(),
        unsafe_allow_html=True,
    )
