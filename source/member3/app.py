"""
Autonomous Campus Crisis Agent — Operations Center & Replay Dashboard.
Member 3 Deliverable - Agentic Challenge (Divitiae Tech).
Clean, simplified layout with zero emojis.
"""
import textwrap
import streamlit as st

from src.config import (
    VIEW_INCOMING_REPORT,
    VIEW_DECISION_LOG,
    VIEW_INCIDENT_SUMMARY,
    VIEW_ACTION_HISTORY,
    VIEW_LIST,
)
from src.data_loader import load_all_scenarios, create_scenario_from_upload
from src.replay_engine import ReplayEngine
from src.agent_bridge import to_json_line
from src.components.style import apply_custom_css
from src.components.replay_controls import render_replay_controls, drive_autoplay
from src.views.incoming_report import render_incoming_report_view
from src.views.decision_log import render_decision_log_view
from src.views.incident_summary import render_incident_summary_view
from src.views.action_history import render_action_history_view


def init_session():
    """Initialize Streamlit session state."""
    scenarios = load_all_scenarios()

    if "available_scenarios" not in st.session_state:
        st.session_state["available_scenarios"] = scenarios

    if "current_scenario_id" not in st.session_state:
        default_id = "all_reports" if "all_reports" in scenarios else (list(scenarios.keys())[0] if scenarios else None)
        st.session_state["current_scenario_id"] = default_id

    if "replay_engine" not in st.session_state and st.session_state["current_scenario_id"]:
        selected_scenario = st.session_state["available_scenarios"][st.session_state["current_scenario_id"]]
        st.session_state["replay_engine"] = ReplayEngine(selected_scenario)

    if "is_playing" not in st.session_state:
        st.session_state["is_playing"] = False

    if "current_view" not in st.session_state:
        st.session_state["current_view"] = VIEW_INCOMING_REPORT


def main():
    st.set_page_config(
        page_title="Campus Crisis Operations Center",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_custom_css()
    init_session()

    scenarios = st.session_state["available_scenarios"]
    replay_engine: ReplayEngine = st.session_state.get("replay_engine")

    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.markdown(
            textwrap.dedent("""
<div style="padding: 0.2rem 0 0.8rem 0;">
    <h2 style="margin:0; font-size:1.25rem; color:#818CF8; font-weight:800; letter-spacing:-0.5px;">DIVITIAE TECH</h2>
    <div style="font-size:0.75rem; color:#9CA3AF; text-transform:uppercase; letter-spacing:0.06em;">
        Campus Crisis Command
    </div>
</div>
""").strip(),
            unsafe_allow_html=True,
        )

        st.markdown("#### Scenario Feed")
        scenario_options = {s_id: s.title for s_id, s in scenarios.items()}
        if "pending_scenario_id" in st.session_state:
            st.session_state["current_scenario_id"] = st.session_state.pop("pending_scenario_id")

        def on_scenario_change():
            st.session_state["replay_engine"] = ReplayEngine(scenarios[st.session_state["current_scenario_id"]])
            st.session_state["is_playing"] = False
            # The scrub slider keeps its session-state value across scenario
            # switches otherwise (see replay_controls.py note), which could
            # desync it from the freshly reset engine if the old position
            # happens to still be in-range for the new scenario.
            st.session_state["scrub_slider"] = 0

        st.selectbox(
            "Select Scenario",
            options=list(scenario_options.keys()),
            format_func=lambda x: scenario_options.get(x, x),
            key="current_scenario_id",
            on_change=on_scenario_change,
            label_visibility="collapsed",
        )

        # Upload Test CSV (Optional)
        with st.expander("Upload Custom Test CSV"):
            st.caption("Upload unseen test CSV to evaluate live.")
            uploaded_file = st.file_uploader("Upload CSV file", type=["csv"], label_visibility="collapsed")
            # The uploader keeps returning the file on every rerun; process it once.
            if uploaded_file is not None and uploaded_file.file_id != st.session_state.get("processed_upload_id"):
                st.session_state["processed_upload_id"] = uploaded_file.file_id
                new_scenario = create_scenario_from_upload(uploaded_file)
                if new_scenario:
                    st.session_state["available_scenarios"][new_scenario.scenario_id] = new_scenario
                    # The scenario selectbox is already rendered; select it on the next run.
                    st.session_state["pending_scenario_id"] = new_scenario.scenario_id
                    st.session_state["replay_engine"] = ReplayEngine(new_scenario)
                    st.session_state["is_playing"] = False
                    st.session_state["scrub_slider"] = 0
                    st.rerun()

        st.markdown("---")

        # View Navigation
        st.markdown("#### Dashboard Views")
        # Keyed widget: passing a state-derived index instead makes Streamlit
        # rebuild the radio each rerun and drop the next click.
        st.radio(
            "Select View",
            options=VIEW_LIST,
            key="current_view",
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Export predictions.jsonl
        all_preds = replay_engine.get_cumulative_predictions()
        jsonl_content = "".join(to_json_line(p.model_dump()) + "\n" for p in all_preds)
        st.download_button(
            f"Download predictions.jsonl ({len(all_preds)} rows)",
            data=jsonl_content.encode("utf-8"),
            file_name="predictions.jsonl",
            mime="application/x-ndjson",
            use_container_width=True,
        )

    # ==================== MAIN PANEL ====================
    # Clean Header
    st.markdown(
        textwrap.dedent("""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
    <div>
        <h2 style="margin:0 0 4px 0; font-size:1.45rem; color:#FFFFFF; font-weight:700; line-height:1.35;">Campus Crisis Operations Center</h2>
        <div style="color:#9CA3AF; font-size:0.82rem;">Autonomous Incident Correlation & Sequential Evidence Replay</div>
    </div>
    <span class="badge-pill" style="background:rgba(16, 185, 129, 0.15); border:1px solid #10B981; color:#34D399;">
        ACTIVE
    </span>
</div>
""").strip(),
        unsafe_allow_html=True,
    )

    if not replay_engine or replay_engine.total_ticks == 0:
        st.error("No reports found in scenario.")
        return

    # Compact Replay Controller
    render_replay_controls(replay_engine)

    st.markdown("---")

    # Render Selected View
    current_view = st.session_state["current_view"]

    if current_view == VIEW_INCOMING_REPORT:
        render_incoming_report_view(replay_engine)
    elif current_view == VIEW_DECISION_LOG:
        render_decision_log_view(replay_engine)
    elif current_view == VIEW_INCIDENT_SUMMARY:
        render_incident_summary_view(replay_engine)
    elif current_view == VIEW_ACTION_HISTORY:
        render_action_history_view(replay_engine)

    # Must run last: advances one tick and reruns if Play is active. Doing
    # this after the view above has rendered means the just-advanced
    # report/incident state is actually painted each step, instead of
    # frozen while the engine silently keeps advancing (st.rerun() aborts
    # everything after its call site, so this can't run any earlier).
    drive_autoplay(replay_engine)


if __name__ == "__main__":
    main()
