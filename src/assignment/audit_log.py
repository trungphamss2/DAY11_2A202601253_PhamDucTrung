"""
Assignment 11 — Audit Log starter (TODO).

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


import json
import time
from datetime import datetime, timezone
from pathlib import Path


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, dict] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None):
        """Store input + start timestamp keyed by request_id/user_id."""
        key = request_id or user_id
        self._open[key] = {
            "start_time": time.time(),
            "user_id": user_id,
            "text": text,
            "request_id": request_id,
        }

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ):
        """Store output, layer decision, latency; append to self.logs."""
        key = request_id or user_id
        input_data = self._open.pop(key, {})
        start_time = input_data.get("start_time", time.time())
        latency_ms = (time.time() - start_time) * 1000

        entry = {
            "request_id": request_id or input_data.get("request_id"),
            "user_id": user_id,
            "timestamp": utc_now_iso(),
            "input_text": input_data.get("text", ""),
            "output_preview": text[:200] if text else "",
            "blocked": blocked,
            "layer": layer,
            "latency_ms": round(latency_ms, 2),
        }
        self.logs.append(entry)

    def find_by_request_id(self, request_id: str) -> list[dict]:
        """Retrieve audit log entries matching a specific request_id."""
        return [log for log in self.logs if log.get("request_id") == request_id]

    def export_json(self, filepath: str = "outputs/audit_log.json"):
        """Write logs to disk (JSON array)."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.logs, ensure_ascii=False, indent=2), encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
