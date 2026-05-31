from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PrimeVarClassSecuritySettings:
    api_key: str | None = None

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)


def resolve_security_settings(api_key: str | None = None) -> PrimeVarClassSecuritySettings:
    resolved_api_key = api_key if api_key is not None else os.environ.get("PRIMEVARCLASS_API_KEY")
    return PrimeVarClassSecuritySettings(api_key=resolved_api_key or None)


def verify_api_key(provided_api_key: str | None, expected_api_key: str | None) -> bool:
    if not expected_api_key:
        return True
    if not provided_api_key:
        return False
    return secrets.compare_digest(str(provided_api_key), str(expected_api_key))


def mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return f"{api_key[:2]}{'*' * max(1, len(api_key) - 4)}{api_key[-2:]}"
