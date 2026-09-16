"""
CSS styling for Campus Crisis Agent.
Clean, modern dark theme. No emojis.
"""
import streamlit as st
from src.config import SEVERITY_COLORS, STATUS_COLORS, RELATIONSHIP_COLORS


def apply_custom_css():
    """Inject clean CSS styling."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    .block-container {
        padding-top: 3.6rem !important;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }

    /* Clean Info Box */
    .info-box {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }

    /* Metric Cards */
    .metric-card {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        height: 100%;
        box-sizing: border-box;
    }

    .metric-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 700;
        color: #9CA3AF;
        margin-bottom: 0.35rem;
    }

    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }

    .metric-sub {
        font-size: 0.75rem;
        color: #6B7280;
    }

    /* Clean Badge Pills with Uniform Height & Alignment */
    .badge-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        height: 26px;
        padding: 0 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        line-height: 1;
        vertical-align: middle;
        box-sizing: border-box;
        white-space: nowrap;
    }

    /* Slider vertical alignment */
    div[data-testid="stSlider"] {
        padding-top: 0.35rem;
        padding-bottom: 0.15rem;
    }

    /* Clean Buttons */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        height: 38px;
        line-height: 38px;
        padding: 0 12px;
        box-sizing: border-box;
        border: 1px solid #374151;
        background: #1F2937;
        color: #F3F4F6;
        transition: all 0.15s ease;
    }

    .stButton>button:hover {
        background: #374151;
        border-color: #4B5563;
        color: #FFFFFF;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def get_severity_badge_html(severity: str) -> str:
    """Return colored badge for severity."""
    sev = severity.upper()
    color = SEVERITY_COLORS.get(sev, "#9CA3AF")
    bg = f"{color}22"
    return f'<span class="badge-pill" style="background:{bg}; color:{color}; border:1px solid {color};">{sev}</span>'


def get_status_badge_html(status: str) -> str:
    """Return colored badge for status."""
    st_val = status.upper()
    color = STATUS_COLORS.get(st_val, "#9CA3AF")
    bg = f"{color}22"
    return f'<span class="badge-pill" style="background:{bg}; color:{color}; border:1px solid {color};">{st_val}</span>'


def get_relationship_badge_html(rel: str) -> str:
    """Return colored badge for relationship."""
    r_val = rel.upper()
    color = RELATIONSHIP_COLORS.get(r_val, "#6366F1")
    bg = f"{color}22"
    return f'<span class="badge-pill" style="background:{bg}; color:{color}; border:1px solid {color};">{r_val}</span>'


def get_incident_badge_html(incident_id: str) -> str:
    """Return colored badge for incident ID."""
    return f'<span class="badge-pill" style="background:#1F2937; color:#818CF8; border:1px solid #374151; font-family:\'JetBrains Mono\', monospace;">Incident {incident_id}</span>'


def get_human_review_badge_html(human_review: bool) -> str:
    """Return badge if human review is flagged."""
    if human_review:
        return '<span class="badge-pill" style="background:rgba(239, 68, 68, 0.2); color:#F87171; border:1px solid #EF4444;">REVIEW REQUIRED</span>'
    return '<span class="badge-pill" style="background:rgba(16, 185, 129, 0.12); color:#34D399; border:1px solid #10B981;">AUTO</span>'


def get_action_badge_html(action_type: str, is_new_action: bool = True) -> str:
    """Distinguish new actions from continued actions as required by checklist."""
    if is_new_action and action_type != "CONTINUE_RESPONSE":
        return f'<span class="badge-pill" style="background:rgba(6, 182, 212, 0.18); color:#06B6D4; border:1px solid #06B6D4;">[NEW] {action_type}</span>'
    else:
        return f'<span class="badge-pill" style="background:rgba(148, 163, 184, 0.15); color:#94A3B8; border:1px solid #475569;">[CONTINUED] {action_type}</span>'
