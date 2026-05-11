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


def _normalize_team_id(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", lowered).strip("-")
    return normalized


def _normalize_profile_id(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", lowered).strip("-")
    return normalized


def _guest_team(requested_team_id: str | None = None) -> dict:
    return {
        "team_id": "solo",
        "display_name": "Workspace local",
        "institution": None,
        "description": None,
        "metadata": {},
        "created_at": None,
        "updated_at": None,
        "last_used_at": None,
        "member_role": None,
        "is_guest": True,
        "requested_team_id": requested_team_id,
        "n_members": 0,
    }


class PrimeVarClassTeamStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._team_file = self.root_dir / "teams.json"
        self._teams: Dict[str, dict] = {}
        self._memberships: Dict[str, Dict[str, dict]] = {}
        self._load_existing_state()

    @property
    def team_file_path(self) -> str:
        return str(self._team_file.resolve())

    def _persist_unlocked(self) -> None:
        payload = {
            "teams": list(self._teams.values()),
            "memberships": {
                team_id: list(members.values())
                for team_id, members in self._memberships.items()
            },
        }
        self._team_file.write_text(
            json.dumps(_to_jsonable(payload), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_existing_state(self) -> None:
        if not self._team_file.exists():
            return
        try:
            payload = json.loads(self._team_file.read_text(encoding="utf-8"))
        except Exception:
            return
        for item in payload.get("teams", []):
            if not isinstance(item, dict):
                continue
            team_id = _normalize_team_id(str(item.get("team_id") or ""))
            if not team_id:
                continue
            normalized = dict(item)
            normalized["team_id"] = team_id
            normalized["metadata"] = _to_jsonable(dict(normalized.get("metadata", {})))
            self._teams[team_id] = normalized

        for team_id, members in dict(payload.get("memberships", {})).items():
            normalized_team_id = _normalize_team_id(str(team_id))
            if not normalized_team_id:
                continue
            member_map: Dict[str, dict] = {}
            for item in members or []:
                if not isinstance(item, dict):
                    continue
                profile_id = _normalize_profile_id(str(item.get("profile_id") or ""))
                if not profile_id:
                    continue
                normalized = dict(item)
                normalized["profile_id"] = profile_id
                normalized["team_id"] = normalized_team_id
                member_map[profile_id] = normalized
            self._memberships[normalized_team_id] = member_map

    def upsert_team(
        self,
        team_id: str | None,
        display_name: str,
        institution: str | None = None,
        description: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> dict:
        resolved_team_id = _normalize_team_id(team_id or display_name)
        if not resolved_team_id:
            raise ValueError("Nao foi possivel gerar um identificador valido para o time.")
        if not display_name.strip():
            raise ValueError("display_name nao pode ser vazio.")

        now = _now_utc()
        with self._lock:
            existing = self._teams.get(resolved_team_id, {})
            team = {
                "team_id": resolved_team_id,
                "display_name": display_name.strip(),
                "institution": institution.strip() if isinstance(institution, str) and institution.strip() else None,
                "description": description.strip() if isinstance(description, str) and description.strip() else None,
                "metadata": _to_jsonable(dict(metadata or {})),
                "created_at": existing.get("created_at") or now,
                "updated_at": now,
                "last_used_at": existing.get("last_used_at"),
                "is_guest": False,
            }
            self._teams[resolved_team_id] = team
            self._memberships.setdefault(resolved_team_id, {})
            self._persist_unlocked()
            return self._decorate_team_unlocked(team, None)

    def _decorate_team_unlocked(self, team: dict, member_role: str | None) -> dict:
        team_id = str(team["team_id"])
        member_count = len(self._memberships.get(team_id, {}))
        resolved = dict(team)
        resolved["member_role"] = member_role
        resolved["is_guest"] = False
        resolved["n_members"] = member_count
        return resolved

    def list_teams(self) -> List[dict]:
        with self._lock:
            teams = [self._decorate_team_unlocked(item, None) for item in self._teams.values()]
        teams.sort(
            key=lambda item: str(item.get("last_used_at") or item.get("updated_at") or ""),
            reverse=True,
        )
        return teams

    def get_team(self, team_id: str) -> dict:
        resolved_team_id = _normalize_team_id(team_id)
        with self._lock:
            if resolved_team_id not in self._teams:
                raise KeyError(f"Time nao encontrado: {team_id}")
            return self._decorate_team_unlocked(self._teams[resolved_team_id], None)

    def assign_member(self, team_id: str, profile_id: str, team_role: str = "member") -> dict:
        resolved_team_id = _normalize_team_id(team_id)
        resolved_profile_id = _normalize_profile_id(profile_id)
        if not resolved_team_id or not resolved_profile_id:
            raise ValueError("team_id e profile_id precisam ser validos.")
        now = _now_utc()
        with self._lock:
            if resolved_team_id not in self._teams:
                raise KeyError(f"Time nao encontrado: {team_id}")
            member_map = self._memberships.setdefault(resolved_team_id, {})
            existing = member_map.get(resolved_profile_id, {})
            membership = {
                "team_id": resolved_team_id,
                "profile_id": resolved_profile_id,
                "team_role": (team_role or "member").strip(),
                "created_at": existing.get("created_at") or now,
                "updated_at": now,
                "last_used_at": existing.get("last_used_at"),
                "status": "active",
            }
            member_map[resolved_profile_id] = membership
            self._persist_unlocked()
            return dict(membership)

    def list_members(self, team_id: str) -> List[dict]:
        resolved_team_id = _normalize_team_id(team_id)
        with self._lock:
            if resolved_team_id not in self._teams:
                raise KeyError(f"Time nao encontrado: {team_id}")
            members = [dict(item) for item in self._memberships.get(resolved_team_id, {}).values()]
        members.sort(key=lambda item: str(item.get("profile_id") or ""))
        return members

    def get_membership(self, team_id: str, profile_id: str | None) -> dict | None:
        if not profile_id:
            return None
        resolved_team_id = _normalize_team_id(team_id)
        resolved_profile_id = _normalize_profile_id(profile_id)
        with self._lock:
            return dict(self._memberships.get(resolved_team_id, {}).get(resolved_profile_id) or {}) or None

    def mark_team_used(self, team_id: str, profile_id: str | None = None) -> dict:
        resolved_team_id = _normalize_team_id(team_id)
        resolved_profile_id = _normalize_profile_id(profile_id) if profile_id else None
        with self._lock:
            if resolved_team_id not in self._teams:
                return _guest_team(requested_team_id=resolved_team_id)
            team = self._teams[resolved_team_id]
            team["last_used_at"] = _now_utc()
            member_role = None
            if resolved_profile_id:
                membership = self._memberships.get(resolved_team_id, {}).get(resolved_profile_id)
                if membership is not None:
                    membership["last_used_at"] = _now_utc()
                    member_role = membership.get("team_role")
            self._persist_unlocked()
            return self._decorate_team_unlocked(team, member_role)

    def resolve_team(self, team_id: str | None, profile_id: str | None = None) -> dict:
        if not team_id:
            return _guest_team()
        resolved_team_id = _normalize_team_id(team_id)
        resolved_profile_id = _normalize_profile_id(profile_id) if profile_id else None
        with self._lock:
            team = self._teams.get(resolved_team_id)
            if team is None:
                return _guest_team(requested_team_id=resolved_team_id)
            membership = self._memberships.get(resolved_team_id, {}).get(resolved_profile_id) if resolved_profile_id else None
            member_role = membership.get("team_role") if membership else None
            return self._decorate_team_unlocked(team, member_role)
