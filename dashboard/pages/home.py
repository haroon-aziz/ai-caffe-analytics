from __future__ import annotations

from datetime import datetime, timedelta

from utils.timeutils import utcnow

import streamlit as st

from analytics import aggregates
from dashboard import state
from dashboard.components.cards import (
    app_header,
    empty_state,
    kpi_row,
    render_alerts,
    section_title,
    status_pill,
)
from dashboard.components.charts import bar_chart, line_chart
from dashboard.theme import PALETTE


def _fmt_seconds(seconds: float) -> str:
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"


def render() -> None:
    app_header("Smart Cafe Analytics", "Real-time business intelligence for your cafe")

    db = state.get_database()
    orch = state.get_orchestrator(create=False)
    running = state.is_running()

    pill = status_pill("● Live", "ok") if running else status_pill("Idle", "idle")
    src = st.session_state.get("source_label") or "—"
    st.markdown(
        f"{pill} &nbsp; <span style='color:{PALETTE['muted']}'>Source: {src}</span>",
        unsafe_allow_html=True,
    )

    metrics = orch.metrics() if orch is not None else None
    k = metrics.kpis() if metrics is not None else {}

    total_visitors = k.get("total_visitors") or db.count_visits(role="customer")
    peak = k.get("peak_hour")
    peak_str = f"{peak:02d}:00" if peak is not None else "—"

    section_title("Live KPIs", "📊")
    cards = [
        {"label": "Current Customers", "value": k.get("current_customers", 0), "icon": "🧑‍🤝‍🧑",
         "accent": PALETTE["primary"]},
        {"label": "Today's Visitors", "value": total_visitors, "icon": "🚪",
         "accent": PALETTE["accent"]},
        {"label": "Occupancy", "value": f"{k.get('occupancy_percentage', 0):.0f}%", "icon": "🪑",
         "accent": PALETTE["success"]},
        {"label": "Avg Stay", "value": _fmt_seconds(k.get("avg_stay_seconds", 0)), "icon": "⏱️",
         "accent": PALETTE["warning"]},
        {"label": "Occupied Tables", "value": k.get("occupied_tables", 0), "icon": "✅",
         "accent": PALETTE["success"]},
        {"label": "Empty Tables", "value": k.get("empty_tables", 0), "icon": "⬜",
         "accent": PALETTE["muted"]},
        {"label": "Queue Length", "value": k.get("queue_length", 0), "icon": "🧾",
         "accent": PALETTE["danger"] if k.get("queue_length", 0) else PALETTE["accent"]},
        {"label": "Staff Present", "value": k.get("current_staff", 0), "icon": "👔",
         "accent": PALETTE["accent"]},
        {"label": "Avg Wait", "value": _fmt_seconds(k.get("avg_wait_seconds", 0)), "icon": "⌛",
         "accent": PALETTE["warning"]},
        {"label": "Peak Hour", "value": peak_str, "icon": "📈", "accent": PALETTE["primary"]},
        {"label": "Max Occupancy", "value": k.get("max_occupancy", 0), "icon": "🔝",
         "accent": PALETTE["accent"]},
        {"label": "FPS", "value": k.get("fps", 0), "icon": "🎥", "accent": PALETTE["success"]},
    ]
    kpi_row(cards, columns=4)

    col1, col2 = st.columns([2, 1])
    with col1:
        section_title("Occupancy Trend", "📉")
        snaps = db.get_snapshots(
            session_id=orch.session_id if orch else None,
            since=utcnow() - timedelta(hours=6),
        )
        if snaps:
            xs = [s.timestamp for s in snaps]
            ys = [s.current_customers for s in snaps]
            st.plotly_chart(line_chart(xs, ys, name="Customers"), use_container_width=True)
        else:
            empty_state("No occupancy data yet", "📉",
                        "Start a camera or upload a video to see live trends.")
    with col2:
        section_title("Alerts", "🔔")
        live_alerts = metrics.alerts if metrics is not None else []
        if live_alerts:
            render_alerts(live_alerts)
        else:
            recent = db.get_alerts(limit=6)
            render_alerts(
                [{"message": a.message, "severity": a.severity} for a in recent],
                empty_msg="No active alerts",
            )

    section_title("Visitors by Hour", "🕒")
    hourly = aggregates.hourly_visitors(db, role="customer")
    if any(hourly.values()):
        labels = [f"{h:02d}" for h in hourly.keys()]
        st.plotly_chart(
            bar_chart(labels, list(hourly.values()), name="Visitors"),
            use_container_width=True,
        )
    else:
        empty_state("No visitor history yet", "🕒")
