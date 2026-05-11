from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


class PrimeVarClassAuditLogger:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._audit_file = self.root_dir / "audit_events.ndjson"

    @property
    def audit_file_path(self) -> str:
        return str(self._audit_file.resolve())

    def log_event(
        self,
        event_type: str,
        status: str = "info",
        actor: str | None = None,
        request_path: str | None = None,
        job_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> dict:
        event = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "timestamp": _now_utc(),
            "event_type": event_type,
            "status": status,
            "actor": actor or "system",
            "request_path": request_path,
            "job_id": job_id,
            "metadata": _to_jsonable(metadata or {}),
        }
        with self._lock:
            with self._audit_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def list_events(self, limit: int = 100) -> List[dict]:
        if not self._audit_file.exists():
            return []
        lines = self._audit_file.read_text(encoding="utf-8").splitlines()
        events = []
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        events.reverse()
        return events
