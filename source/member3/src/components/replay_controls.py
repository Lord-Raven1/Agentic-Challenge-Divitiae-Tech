"""
Clean, minimal Replay Controller for Campus Crisis Agent.
Zero emojis, high usability.
"""
import time
import textwrap
import streamlit as st
from src.replay_engine import ReplayEngine
from src.config import REPLAY_SPEED_MAP


def render_replay_controls(replay_engine: ReplayEngine):
    """Render a compact, single-row replay control bar."""
    cur_tick = replay_engine.get_current_tick()
    total_ticks = replay_engine.total_ticks
    cur_idx = replay_engine.current_tick_idx
    rep = cur_tick.report
    pred = cur_tick.prediction

    # Single compact status line
    st.markdown(
        textwrap.dedent(f"""
<div style="background:#111827; border:1px solid #374151; border-radius:6px; padding:0.6rem 1rem; margin-bottom:0.8rem; display:flex; justify-content:space-between; align-items:center; font-size:0.85rem;">
    <div>
        <strong>{replay_engine.scenario.title}</strong> &nbsp;|&nbsp; 
        Report <strong style="color:#818CF8;">{rep.report_id}</strong> ({cur_idx + 1} of {total_ticks}) &nbsp;|&nbsp; 
        Location: <span style="color:#E5E7EB;">{rep.clean_location}</span>
    </div>
    <div>
        Incident: <strong style="color:#818CF8;">{pred.incident_id}</strong> &nbsp;|&nbsp; 
        Severity: <strong style="color:#FBBF24;">{pred.severity}</strong> &nbsp;|&nbsp; 
        Confidence: <strong style="color:#10B981;">{pred.confidence * 100:.0f}%</strong>
    </div>
</div>
""").strip(),
        unsafe_allow_html=True,
    )

    # 4 Clear Buttons + Scrubber Slider + Speed dropdown
    col_ctrl, col_slider, col_speed = st.columns([4, 6, 2])

    with col_ctrl:
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("Previous", use_container_width=True):
                replay_engine.step_prev()
                st.session_state["scrub_slider"] = replay_engine.current_tick_idx
                st.session_state["is_playing"] = False
                st.rerun()
        with b2:
            is_playing = st.session_state.get("is_playing", False)
            play_label = "Pause" if is_playing else "Play"
            if st.button(play_label, use_container_width=True):
                st.session_state["is_playing"] = not is_playing
                st.rerun()
        with b3:
            if st.button("Next", use_container_width=True):
                replay_engine.step_next()
                st.session_state["scrub_slider"] = replay_engine.current_tick_idx
                st.session_state["is_playing"] = False
                st.rerun()
        with b4:
            if st.button("Reset", use_container_width=True):
                replay_engine.reset()
                st.session_state["scrub_slider"] = replay_engine.current_tick_idx
                st.session_state["is_playing"] = False
                st.rerun()

    with col_slider:
        # NOTE: once a widget with this `key` has rendered once, Streamlit
        # ignores `value=` on every later rerun and uses
        # st.session_state["scrub_slider"] instead — so Previous/Next/Reset/
        # Play must write that key directly (above and below) whenever they
        # move the engine's position, or their step gets silently reverted
        # here on the very next rerun.
        slider_val = st.slider(
            "Scrub Report Position",
            min_value=0,
            max_value=max(0, total_ticks - 1),
            value=cur_idx,
            label_visibility="collapsed",
            key="scrub_slider",
        )
        if slider_val != cur_idx:
            replay_engine.jump_to_tick(slider_val)
            st.session_state["is_playing"] = False
            st.rerun()

    with col_speed:
        speed_choice = st.selectbox(
            "Replay Speed",
            options=list(REPLAY_SPEED_MAP.keys()),
            index=1,
            label_visibility="collapsed",
        )
        replay_engine.speed_seconds = REPLAY_SPEED_MAP[speed_choice]

    # Handle automatic playback
    if st.session_state.get("is_playing", False):
        if not replay_engine.is_finished:
            time.sleep(replay_engine.speed_seconds)
            replay_engine.step_next()
            st.session_state["scrub_slider"] = replay_engine.current_tick_idx
            st.rerun()
        else:
            st.session_state["is_playing"] = False
            st.rerun()
