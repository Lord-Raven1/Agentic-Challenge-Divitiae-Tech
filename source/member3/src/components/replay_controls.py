"""
Clean, minimal Replay Controller for Campus Crisis Agent.
Zero emojis, high usability.
"""
import time
import textwrap
import streamlit as st
from src.replay_engine import ReplayEngine
from src.config import REPLAY_SPEED_MAP


def _move_engine(action) -> None:
    """Run an engine-mutating action, flag that the slider's session state
    needs to be re-synced to the engine on the next run, then rerun.

    The flag matters: syncing st.session_state["scrub_slider"] unconditionally
    on every run would also clobber a genuine user slider drag before the
    code below ever gets to detect and apply it (a real regression this
    caused once — Member 3's AppTest-based test caught it, since it drives
    the slider the same way a real drag does). Only Previous/Next/Reset/
    autoplay should force a re-sync; a slider drag should not.
    """
    action()
    st.session_state["is_playing"] = False
    st.session_state["_sync_slider"] = True
    st.rerun()


def render_replay_controls(replay_engine: ReplayEngine):
    """Render a compact, single-row replay control bar."""
    # Only mirror the engine's position into the slider's session state when
    # something OTHER than the slider itself moved the engine (see
    # _move_engine above) — and only here, before the slider widget is
    # instantiated this run. Once a widget with a given `key` has rendered
    # in this run, Streamlit (a) ignores `value=` on it and reads
    # st.session_state[key] instead, and (b) raises
    # StreamlitWidgetAlreadyInstantiatedError if you write that key
    # afterwards — so this has to happen exactly once, right here.
    if st.session_state.pop("_sync_slider", False):
        st.session_state["scrub_slider"] = replay_engine.current_tick_idx

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
                _move_engine(replay_engine.step_prev)
        with b2:
            is_playing = st.session_state.get("is_playing", False)
            play_label = "Pause" if is_playing else "Play"
            if st.button(play_label, use_container_width=True):
                st.session_state["is_playing"] = not is_playing
                st.rerun()
        with b3:
            if st.button("Next", use_container_width=True):
                _move_engine(replay_engine.step_next)
        with b4:
            if st.button("Reset", use_container_width=True):
                _move_engine(replay_engine.reset)

    with col_slider:
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


def drive_autoplay(replay_engine: ReplayEngine) -> None:
    """Advance one tick and rerun if playing. Must be called at the very
    end of the page (after the selected view has rendered), NOT from
    inside render_replay_controls: st.rerun() aborts the rest of the
    script immediately, so anything after the call site never executes on
    that pass. Calling it here means the just-rendered report/incident/view
    state is fully painted before the script loops to advance again;
    calling it any earlier leaves everything downstream visually frozen
    while the engine's position keeps advancing underneath it."""
    if st.session_state.get("is_playing", False):
        if not replay_engine.is_finished:
            time.sleep(replay_engine.speed_seconds)
            replay_engine.step_next()
            st.session_state["_sync_slider"] = True
            st.rerun()
        else:
            st.session_state["is_playing"] = False
            st.rerun()
