from __future__ import annotations

import streamlit as st

from config import get_config
from dashboard import state
from dashboard.pages import (
    about,
    analytics,
    heatmap,
    home,
    live,
    occupancy,
    reports,
    settings,
    upload,
)
from dashboard.theme import inject_css


_cfg = get_config()
st.set_page_config(
    page_title=_cfg.dashboard.title,
    page_icon=_cfg.dashboard.icon,
    layout="wide",
    initial_sidebar_state="expanded",
)


PAGES = {
    "Home": ("🏠", home.render),
    "Live Camera": ("📷", live.render),
    "Video Upload": ("🎬", upload.render),
    "Analytics": ("📊", analytics.render),
    "Occupancy": ("🪑", occupancy.render),
    "Heatmap": ("🔥", heatmap.render),
    "Reports": ("📄", reports.render),
    "Settings": ("⚙️", settings.render),
    "About": ("ℹ️", about.render),
}


def _sidebar() -> str:
    with st.sidebar:
        st.markdown(
            f'<div class="ca-brand">{_cfg.dashboard.icon} {_cfg.dashboard.title}</div>',
            unsafe_allow_html=True,
        )
        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            format_func=lambda k: f"{PAGES[k][0]}  {k}",
            label_visibility="collapsed",
        )
        st.divider()

        if state.is_running():
            st.success(f"● Live · {st.session_state.get('source_label', '')}")
            if st.button("⏹ Stop session", use_container_width=True):
                state.stop_source()
                st.rerun()
        else:
            st.caption("No active source")
        st.caption("CafeAnalytics · Python + Streamlit")
    return choice


def main() -> None:
    st.markdown(inject_css(), unsafe_allow_html=True)
    state.ensure_state()
    choice = _sidebar()
    _, render_fn = PAGES[choice]
    render_fn()


main()
