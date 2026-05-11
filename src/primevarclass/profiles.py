from __future__ import annotations

import json
import re
import threading
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


def _normalize_profile_id(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", lowered).strip("-")
    return normalized


def _guest_profile(requested_profile_id: str | None = None) -> dict:
    return {
        "profile_id": "guest",
        "display_name": "Operador local",
        "role": "guest",
        "institution": None,
        "email": None,
        "metadata": {},
        "created_at": None,
        "updated_at": None,
        "last_used_at": None,
        "is_guest": True,
        "requested_profile_id": requested_profile_id,
    }


class PrimeVarClassProfileStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._profile_file = self.root_dir / "user_profiles.json"
        self._profiles: Dict[str, dict] = {}
        self._load_existing_profiles()

    @property
    def profile_file_path(self) -> str:
        return str(self._profile_file.resolve())

    def _persist_unlocked(self) -> None:
        payload = {
            "profiles": list(self._profiles.values()),
        }
        self._profile_file.write_text(
            json.dumps(_to_jsonable(payload), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_existing_profiles(self) -> None:
        if not self._profile_file.exists():
            return
        try:
            payload = json.loads(self._profile_file.read_text(encoding="utf-8"))
        except Exception:
            return
        profiles = payload.get("profiles", [])
        if not isinstance(profiles, list):
            return
        for item in profiles:
            if not isinstance(item, dict):
                continue
            profile_id = _normalize_profile_id(str(item.get("profile_id") or ""))
            if not profile_id:
                continue
            normalized = dict(item)
            normalized["profile_id"] = profile_id
            normalized["is_guest"] = False
            normalized["metadata"] = _to_jsonable(dict(normalized.get("metadata", {})))
            self._profiles[profile_id] = normalized

    def upsert_profile(
        self,
        profile_id: str | None,
        display_name: str,
        role: str = "researcher",
        institution: str | None = None,
        email: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> dict:
        resolved_profile_id = _normalize_profile_id(profile_id or display_name)
        if not resolved_profile_id:
            raise ValueError("Nao foi possivel gerar um identificador valido para o perfil.")
        if not display_name.strip():
            raise ValueError("display_name nao pode ser vazio.")

        now = _now_utc()
        with self._lock:
            existing = self._profiles.get(resolved_profile_id, {})
            profile = {
                "profile_id": resolved_profile_id,
                "display_name": display_name.strip(),
                "role": (role or "researcher").strip(),
                "institution": institution.strip() if isinstance(institution, str) and institution.strip() else None,
                "email": email.strip() if isinstance(email, str) and email.strip() else None,
                "metadata": _to_jsonable(dict(metadata or {})),
                "created_at": existing.get("created_at") or now,
                "updated_at": now,
                "last_used_at": existing.get("last_used_at"),
                "is_guest": False,
            }
            self._profiles[resolved_profile_id] = profile
            self._persist_unlocked()
            return dict(profile)

    def list_profiles(self) -> List[dict]:
        with self._lock:
            profiles = [dict(item) for item in self._profiles.values()]
        profiles.sort(
            key=lambda item: str(item.get("last_used_at") or item.get("updated_at") or ""),
            reverse=True,
        )
        return profiles

    def get_profile(self, profile_id: str) -> dict:
        resolved_profile_id = _normalize_profile_id(profile_id)
        with self._lock:
            if resolved_profile_id not in self._profiles:
                raise KeyError(f"Perfil nao encontrado: {profile_id}")
            return dict(self._profiles[resolved_profile_id])

    def resolve_profile(self, profile_id: str | None) -> dict:
        if not profile_id:
            return _guest_profile()
        resolved_profile_id = _normalize_profile_id(profile_id)
        with self._lock:
            profile = self._profiles.get(resolved_profile_id)
            if profile is None:
                return _guest_profile(requested_profile_id=resolved_profile_id)
            return dict(profile)

    def mark_profile_used(self, profile_id: str | None) -> dict:
        if not profile_id:
            return _guest_profile()
        resolved_profile_id = _normalize_profile_id(profile_id)
        with self._lock:
            profile = self._profiles.get(resolved_profile_id)
            if profile is None:
                return _guest_profile(requested_profile_id=resolved_profile_id)
            profile["last_used_at"] = _now_utc()
            profile["is_guest"] = False
            self._persist_unlocked()
            return dict(profile)
