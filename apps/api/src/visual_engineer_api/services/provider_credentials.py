import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from pydantic import SecretStr

from visual_engineer_api.ai_planning.provider_registry import ProviderId
from visual_engineer_api.core.config import get_settings

BYOK_SESSION_COOKIE = "ve_byok_session"
BYOK_COOKIE_PATH = "/api/v1"
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,64}$")
_REAL_PROVIDERS = frozenset(
    {
        ProviderId.ZHIPU,
        ProviderId.QWEN,
        ProviderId.DEEPSEEK,
        ProviderId.DOUBAO,
        ProviderId.KIMI,
    }
)


class CredentialStoreError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class MonotonicClock(Protocol):
    def monotonic(self) -> float: ...


class SystemMonotonicClock:
    def monotonic(self) -> float:
        return time.monotonic()


@dataclass
class _CredentialRecord:
    value: bytearray
    expires_monotonic: float
    expires_at: datetime

    def destroy(self) -> None:
        for index in range(len(self.value)):
            self.value[index] = 0


class EphemeralProviderCredentialStore:
    """Bounded process-local BYOK storage with explicit byte destruction."""

    def __init__(
        self,
        *,
        ttl_seconds: int | None = None,
        max_sessions: int | None = None,
        clock: MonotonicClock | None = None,
    ) -> None:
        settings = get_settings()
        self._ttl_seconds = ttl_seconds or settings.byok_credential_ttl_seconds
        self._max_sessions = max_sessions or settings.byok_max_sessions
        self._clock = clock or SystemMonotonicClock()
        self._lock = threading.RLock()
        self._sessions: dict[str, dict[ProviderId, _CredentialRecord]] = {}

    def connect(
        self,
        session_id: str | None,
        provider_id: ProviderId,
        secret: SecretStr,
    ) -> tuple[str, datetime]:
        if provider_id not in _REAL_PROVIDERS:
            raise CredentialStoreError("byok_real_provider_required")
        raw = secret.get_secret_value()
        if raw != raw.strip() or not 8 <= len(raw) <= 512 or "\x00" in raw:
            raise CredentialStoreError("byok_credential_invalid")
        try:
            encoded = bytearray(raw.encode("utf-8"))
        except UnicodeEncodeError:
            raise CredentialStoreError("byok_credential_invalid") from None

        with self._lock:
            self._purge_expired_locked()
            resolved_session_id = (
                session_id
                if session_id is not None and _SESSION_ID_PATTERN.fullmatch(session_id)
                else secrets.token_urlsafe(32)
            )
            if resolved_session_id not in self._sessions:
                if len(self._sessions) >= self._max_sessions:
                    for index in range(len(encoded)):
                        encoded[index] = 0
                    raise CredentialStoreError("byok_session_capacity_reached")
                self._sessions[resolved_session_id] = {}
            records = self._sessions[resolved_session_id]
            previous = records.pop(provider_id, None)
            if previous is not None:
                previous.destroy()
            expires_at = datetime.now(UTC) + timedelta(seconds=self._ttl_seconds)
            records[provider_id] = _CredentialRecord(
                value=encoded,
                expires_monotonic=self._clock.monotonic() + self._ttl_seconds,
                expires_at=expires_at,
            )
            return resolved_session_id, expires_at

    def connected(self, session_id: str | None) -> dict[ProviderId, datetime]:
        if session_id is None or _SESSION_ID_PATTERN.fullmatch(session_id) is None:
            return {}
        with self._lock:
            self._purge_expired_locked()
            records = self._sessions.get(session_id, {})
            return {provider_id: record.expires_at for provider_id, record in records.items()}

    def secret(self, session_id: str | None, provider_id: ProviderId) -> SecretStr | None:
        if session_id is None or _SESSION_ID_PATTERN.fullmatch(session_id) is None:
            return None
        with self._lock:
            self._purge_expired_locked()
            record = self._sessions.get(session_id, {}).get(provider_id)
            if record is None:
                return None
            return SecretStr(bytes(record.value).decode("utf-8"))

    def disconnect(self, session_id: str | None, provider_id: ProviderId) -> bool:
        if session_id is None or _SESSION_ID_PATTERN.fullmatch(session_id) is None:
            return False
        with self._lock:
            records = self._sessions.get(session_id)
            if records is None:
                return False
            record = records.pop(provider_id, None)
            if record is None:
                return False
            record.destroy()
            if not records:
                self._sessions.pop(session_id, None)
            return True

    def clear(self) -> None:
        with self._lock:
            for records in self._sessions.values():
                for record in records.values():
                    record.destroy()
            self._sessions.clear()

    def _purge_expired_locked(self) -> None:
        now = self._clock.monotonic()
        empty_sessions: list[str] = []
        for session_id, records in self._sessions.items():
            expired = [
                provider_id
                for provider_id, record in records.items()
                if record.expires_monotonic <= now
            ]
            for provider_id in expired:
                records.pop(provider_id).destroy()
            if not records:
                empty_sessions.append(session_id)
        for session_id in empty_sessions:
            self._sessions.pop(session_id, None)


provider_credential_store = EphemeralProviderCredentialStore()
