from __future__ import annotations

import streamlit as st

from dashboard import state
from dashboard.components.cards import app_header, empty_state, kpi_row, section_title, status_pill
from dashboard.theme import PALETTE
from utils.image import bgr_to_rgb


def _source_controls() -> None:
    section_title("Source", "🎥")
    kind = st.radio(
        "Input type", ["Webcam", "CCTV / RTSP stream"], horizontal=True, label_visibility="collapsed"
    )
    col_a, col_b = st.columns([3, 1])
    with col_a:
        if kind == "Webcam":
            source: object = st.number_input("Webcam index", min_value=0, value=0, step=1)
            label = f"Webcam {source}"
        else:
            source = st.text_input("Stream URL", placeholder="rtsp://user:pass@host:554/stream")
            label = source or "Stream"
    with col_b:
        record = st.toggle("Record", value=False, help="Save an annotated video to outputs/recordings")

    c1, c2, c3 = st.columns(3)
    running = state.is_running()
    if c1.button("▶ Start", use_container_width=True, disabled=running or not str(source)):
        rec_path = None
        if record:
            from datetime import datetime

            rec_path = state.get_config_cached().paths.recordings / (
                datetime.now().strftime("live_%Y%m%d_%H%M%S.mp4")
            )
        state.start_source(source, label=str(label), realtime=True, record_path=rec_path)
        st.rerun()
    if c2.button("⏸ Pause", use_container_width=True, disabled=not running):
        runner = st.session_state.get("runner")
        if runner:
            runner.pause() if runner.state.value == "running" else runner.resume()
    if c3.button("⏹ Stop", use_container_width=True, disabled=not running):
        state.stop_source()
        st.rerun()


@st.fragment(run_every=1.0)
def _live_view() -> None:
    result = state.get_latest_frame_result()
    orch = state.get_orchestrator(create=False)

    if result is None:
        empty_state("Waiting for frames…", "⏳", "The stream is starting up.")
        return

    left, right = st.columns([3, 2])
    with left:
        st.image(bgr_to_rgb(result.annotated_frame), use_container_width=True,
                 caption=f"Frame {result.frame_index} · {result.fps:.1f} FPS")
    with right:
        k = orch.metrics().kpis() if orch else {}
        kpi_row(
            [
                {"label": "People", "value": result.person_count, "icon": "🧑", "accent": PALETTE["primary"]},
                {"label": "FPS", "value": f"{result.fps:.1f}", "icon": "🎥", "accent": PALETTE["success"]},
                {"label": "Customers", "value": k.get("current_customers", 0), "icon": "🧑‍🤝‍🧑", "accent": PALETTE["accent"]},
                {"label": "Staff", "value": k.get("current_staff", 0), "icon": "👔", "accent": PALETTE["warning"]},
            ],
            columns=2,
        )
        section_title("Detections", "🎯")
        rows = [
            {"ID": d.tracker_id, "Class": d.class_name, "Conf": f"{d.confidence:.2f}"}
            for d in result.detections
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True, height=240)
        else:
            st.caption("No tracked objects in view.")

    if st.button("📸 Snapshot", use_container_width=False):
        runner = st.session_state.get("runner")
        if runner:
            path = runner.snapshot(prefix="live")
            if path:
                st.success(f"Snapshot saved: {path.name}")


def render() -> None:
    app_header("Live Camera", "Real-time detection, tracking and analytics")

    running = state.is_running()
    st_state = state.runner_state()
    pill = status_pill("● Live", "ok") if running else status_pill("Stopped", "idle")
    err = ""
    runner = st.session_state.get("runner")
    if runner and runner.stats.last_error:
        pill = status_pill("Error", "err")
        err = runner.stats.last_error
    st.markdown(pill, unsafe_allow_html=True)
    if err:
        st.error(f"Source error: {err}")

    _source_controls()
    st.divider()

    if running:
        _live_view()
    else:
        empty_state(
            "No active source", "📷",
            "Pick a webcam or stream above and press Start. "
            "On a headless server, use a stream URL or the Video Upload page.",
        )
