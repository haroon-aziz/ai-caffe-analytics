from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from utils.timeutils import utcnow
from typing import Dict, List, Optional

from config import Config, get_config
from detection.detections import Detections
from utils.geometry import BBox, Point
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TrackState:
    track_id: int
    class_id: int
    first_seen: datetime
    last_seen: datetime
    first_frame: int
    last_frame: int
    last_box: BBox
    trajectory: List[Point] = field(default_factory=list)
    hits: int = 1
    misses: int = 0
    active: bool = True
    role: str = "customer"
    max_trajectory: int = 1024


    def update(self, box: BBox, anchor: Point, timestamp: datetime, frame_index: int) -> None:
        self.last_box = box
        self.last_seen = timestamp
        self.last_frame = frame_index
        self.hits += 1
        self.misses = 0
        self.active = True
        self.trajectory.append(anchor)
        if len(self.trajectory) > self.max_trajectory:
            self.trajectory = self.trajectory[-self.max_trajectory :]

    def mark_missed(self) -> None:
        self.misses += 1


    @property
    def duration_seconds(self) -> float:
        return (self.last_seen - self.first_seen).total_seconds()

    @property
    def current_anchor(self) -> Optional[Point]:
        return self.trajectory[-1] if self.trajectory else None

    def to_record(self) -> dict:
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "role": self.role,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "duration_seconds": self.duration_seconds,
            "hits": self.hits,
            "trajectory": [[round(x, 1), round(y, 1)] for x, y in self.trajectory],
        }


@dataclass
class TrackFrameResult:
    timestamp: datetime
    frame_index: int
    active_tracks: List[TrackState] = field(default_factory=list)
    entered_tracks: List[TrackState] = field(default_factory=list)
    exited_tracks: List[TrackState] = field(default_factory=list)

    @property
    def active_count(self) -> int:
        return len(self.active_tracks)


class TrackManager:
    def __init__(self, config: Optional[Config] = None, max_trajectory: int = 1024) -> None:
        self.config = config or get_config()
        self.lost_buffer = self.config.tracking.lost_track_buffer
        self.max_trajectory = max_trajectory
        self._states: Dict[int, TrackState] = {}


    def update(
        self,
        detections: Detections,
        timestamp: Optional[datetime] = None,
        frame_index: int = 0,
    ) -> TrackFrameResult:
        ts = timestamp or utcnow()
        entered: List[TrackState] = []
        current_ids: set[int] = set()

        for det in detections:
            if det.tracker_id is None:
                continue
            tid = int(det.tracker_id)
            current_ids.add(tid)
            state = self._states.get(tid)
            if state is None:
                state = TrackState(
                    track_id=tid,
                    class_id=det.class_id,
                    first_seen=ts,
                    last_seen=ts,
                    first_frame=frame_index,
                    last_frame=frame_index,
                    last_box=det.box,
                    trajectory=[det.anchor],
                    max_trajectory=self.max_trajectory,
                )
                self._states[tid] = state
                entered.append(state)
                logger.debug("Track %d entered at frame %d.", tid, frame_index)
            else:
                state.update(det.box, det.anchor, ts, frame_index)

        exited: List[TrackState] = []
        for tid, state in self._states.items():
            if tid in current_ids or not state.active:
                continue
            state.mark_missed()
            if state.misses > self.lost_buffer:
                state.active = False
                exited.append(state)
                logger.debug("Track %d exited (lost > %d frames).", tid, self.lost_buffer)

        active = [s for s in self._states.values() if s.active]
        return TrackFrameResult(
            timestamp=ts,
            frame_index=frame_index,
            active_tracks=active,
            entered_tracks=entered,
            exited_tracks=exited,
        )


    def get_active(self) -> List[TrackState]:
        return [s for s in self._states.values() if s.active]

    def get_track(self, track_id: int) -> Optional[TrackState]:
        return self._states.get(track_id)

    def all_tracks(self) -> List[TrackState]:
        return list(self._states.values())

    def active_count(self, role: Optional[str] = None) -> int:
        return sum(
            1 for s in self._states.values() if s.active and (role is None or s.role == role)
        )

    def total_count(self, role: Optional[str] = None) -> int:
        return sum(1 for s in self._states.values() if role is None or s.role == role)

    def set_role(self, track_id: int, role: str) -> None:
        state = self._states.get(track_id)
        if state is not None:
            state.role = role

    def prune_finished(self, keep_last: int = 0) -> int:
        finished = sorted(
            (s for s in self._states.values() if not s.active),
            key=lambda s: s.last_frame,
            reverse=True,
        )
        to_remove = finished[keep_last:]
        for state in to_remove:
            self._states.pop(state.track_id, None)
        return len(to_remove)

    def reset(self) -> None:
        self._states.clear()
        logger.debug("TrackManager state reset.")
