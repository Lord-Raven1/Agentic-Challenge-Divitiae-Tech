"""
View 4: Action History View.
Displays: action, service, time, and outcome/status for each incident.
Distinguishes new actions from continued actions (CONTINUE_RESPONSE).
Zero emojis, clean layout.
"""
import textwrap
import streamlit as st
import pandas as pd
from src.replay_engine import ReplayEngine
from src.models import ActionHistoryItem


def render_action_history_view(replay_engine: ReplayEngine):
    """Render a clean, simplified Action History View."""
    actions = replay_engine.get_cumulative_actions()

    st.markdown("### Action History")
    st.caption("Log of emergency dispatches, inspections, verifications, and ongoing responses.")

    if not actions:
        st.info("No actions dispatched yet.")
        return

    # 1. Summary Cards (New Dispatches vs Continued Responses)
    new_actions_count = sum(1 for a in actions if a.is_new_action)
    continued_actions_count = sum(1 for a in actions if not a.is_new_action)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Total Actions Recorded</div>
    <div class="metric-val">{len(actions)}</div>
    <div class="metric-sub">Cumulative Action Events</div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Fresh Dispatches</div>
    <div class="metric-val" style="color:#38BDF8;">{new_actions_count}</div>
    <div class="metric-sub">New Deployments Initiated</div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            textwrap.dedent(f"""
<div class="metric-card">
    <div class="metric-label">Continued Responses</div>
    <div class="metric-val" style="color:#9CA3AF;">{continued_actions_count}</div>
    <div class="metric-sub">Avoided Repeat Dispatches</div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 2. Filter Controls
    f1, f2 = st.columns([1, 1])
    with f1:
        all_inc_ids = ["All Incidents"] + sorted(list(set(a.incident_id for a in actions)))
        filter_inc = st.selectbox("Filter by Incident", options=all_inc_ids, key="act_filter_inc_clean")
    with f2:
        all_action_types = ["All Types", "NEW ACTIONS ONLY", "CONTINUED ONLY"] + sorted(list(set(a.action_type for a in actions)))
        filter_type = st.selectbox("Filter by Action Type", options=all_action_types, key="act_filter_type_clean")

    filtered_actions = actions
    if filter_inc != "All Incidents":
        filtered_actions = [a for a in filtered_actions if a.incident_id == filter_inc]
    if filter_type == "NEW ACTIONS ONLY":
        filtered_actions = [a for a in filtered_actions if a.is_new_action]
    elif filter_type == "CONTINUED ONLY":
        filtered_actions = [a for a in filtered_actions if not a.is_new_action]
    elif filter_type != "All Types":
        filtered_actions = [a for a in filtered_actions if a.action_type == filter_type]

    st.markdown(f"**Showing {len(filtered_actions)} of {len(actions)} records**")

    # 3. Action History Table with EXACT Required Columns:
    # action, service, time and outcome/status for each incident
    table_rows = []
    for a in reversed(filtered_actions):
        table_rows.append({
            "Action ID": a.action_id,
            "Incident ID": a.incident_id,
            "Action": a.action_type,
            "Category": "NEW DISPATCH" if a.is_new_action else "CONTINUED (NO REPEAT)",
            "Service": f"{a.service_id} ({a.service_name})",
            "Time": a.time,
            "Status": a.outcome_status,
            "Trigger Report": a.report_id,
        })

    df_actions = pd.DataFrame(table_rows)
    st.dataframe(
        df_actions,
        column_config={
            "Action ID": st.column_config.TextColumn("Action ID", width="small"),
            "Incident ID": st.column_config.TextColumn("Incident ID", width="small"),
            "Action": st.column_config.TextColumn("Action", width="medium"),
            "Category": st.column_config.TextColumn("Action Category", width="medium"),
            "Service": st.column_config.TextColumn("Service", width="large"),
            "Time": st.column_config.TextColumn("Time", width="small"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Trigger Report": st.column_config.TextColumn("Report", width="small"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # 4. Campus Service Directory in clean collapsed expander
    with st.expander("Campus Services Directory (campus_services.csv)"):
        from src.config import SERVICES_CSV
        import csv
        if SERVICES_CSV.exists():
            with open(SERVICES_CSV, "r", encoding="utf-8") as f:
                svc_rows = list(csv.DictReader(f))
            st.table(pd.DataFrame(svc_rows))

    # 5. Export Action History CSV
    csv_bytes = df_actions.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Action History (CSV)",
        data=csv_bytes,
        file_name="action_history.csv",
        mime="text/csv",
        use_container_width=True,
    )
