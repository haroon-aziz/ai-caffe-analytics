from __future__ import annotations

import json
from datetime import datetime, date

from utils.timeutils import utcnow
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JSONEncoded(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return json.loads(value)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Visit(Base, TimestampMixin):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(16), default="customer")
    entry_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_occupancy_seen: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trajectory: Mapped[Optional[list]] = mapped_column(JSONEncoded, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TrackEvent(Base, TimestampMixin):
    __tablename__ = "track_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(16), default="customer")
    zone_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=utcnow)
    details: Mapped[Optional[dict]] = mapped_column(JSONEncoded, nullable=True)


class AnalyticsSnapshot(Base, TimestampMixin):
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=utcnow)
    current_customers: Mapped[int] = mapped_column(Integer, default=0)
    current_staff: Mapped[int] = mapped_column(Integer, default=0)
    occupied_tables: Mapped[int] = mapped_column(Integer, default=0)
    empty_tables: Mapped[int] = mapped_column(Integer, default=0)
    queue_length: Mapped[int] = mapped_column(Integer, default=0)
    avg_wait_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    extra: Mapped[Optional[dict]] = mapped_column(JSONEncoded, nullable=True)


class DailySummary(Base, TimestampMixin):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    summary_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    total_visitors: Mapped[int] = mapped_column(Integer, default=0)
    peak_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    peak_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_stay_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    max_queue_length: Mapped[int] = mapped_column(Integer, default=0)
    avg_wait_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    total_alerts: Mapped[int] = mapped_column(Integer, default=0)
    hourly_visitors: Mapped[Optional[dict]] = mapped_column(JSONEncoded, nullable=True)


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    alert_type: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    message: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=utcnow)
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Zone(Base, TimestampMixin):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    zone_type: Mapped[str] = mapped_column(String(24), index=True)
    points: Mapped[list] = mapped_column(JSONEncoded)
    reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONEncoded, nullable=True)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128))
    report_type: Mapped[str] = mapped_column(String(16))
    file_path: Mapped[str] = mapped_column(String(255))
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONEncoded)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


__all__ = [
    "Base",
    "JSONEncoded",
    "Visit",
    "TrackEvent",
    "AnalyticsSnapshot",
    "DailySummary",
    "Alert",
    "Zone",
    "Report",
    "Setting",
]
