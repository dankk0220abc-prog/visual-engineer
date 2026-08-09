import errno
import socket
import ssl
from collections.abc import Iterator

import httpx

from visual_engineer_api.ai_planning.provider import (
    ProviderError,
    ProviderErrorCategory,
    ProviderTransportPhase,
)

_HTTP_CORE_TRANSPORT_TYPES = frozenset(
    {
        "ConnectError",
        "ConnectTimeout",
        "NetworkError",
        "ReadError",
        "ReadTimeout",
        "RemoteProtocolError",
        "TransportError",
        "WriteError",
        "WriteTimeout",
    }
)
_NETWORK_UNREACHABLE_ERRNOS = frozenset({errno.ENETUNREACH, errno.EHOSTUNREACH})
_MAX_CHAIN_DEPTH = 8


def classify_transport_exception(exception: Exception) -> ProviderError:
    """Map transport types to fixed safe codes without inspecting exception text."""
    chain = tuple(_allowlisted_transport_chain(exception))

    if _contains_type(chain, httpx.ConnectTimeout) or _contains_httpcore_type(
        chain, "ConnectTimeout"
    ):
        return _timeout("provider_connect_timeout", ProviderTransportPhase.CONNECT)
    if _contains_type(chain, httpx.ReadTimeout) or _contains_httpcore_type(chain, "ReadTimeout"):
        return _timeout("provider_read_timeout", ProviderTransportPhase.READ)
    if _contains_type(chain, httpx.WriteTimeout) or _contains_httpcore_type(chain, "WriteTimeout"):
        return _timeout("provider_write_timeout", ProviderTransportPhase.WRITE)
    if _contains_type(chain, httpx.PoolTimeout):
        return _timeout("provider_pool_timeout", ProviderTransportPhase.CONNECT)
    if _contains_type(chain, httpx.TimeoutException):
        return _timeout("provider_timeout", ProviderTransportPhase.TRANSPORT)

    if _contains_type(chain, ssl.SSLCertVerificationError):
        return _transport(
            "provider_tls_certificate_verification_failed",
            ProviderTransportPhase.CONNECT,
        )
    if _contains_type(chain, ssl.SSLError):
        return _transport("provider_tls_handshake_failed", ProviderTransportPhase.CONNECT)
    if _contains_type(chain, socket.gaierror):
        return _transport("provider_dns_resolution_failed", ProviderTransportPhase.CONNECT)
    if _contains_errno(chain, errno.ECONNREFUSED):
        return _transport("provider_connection_refused", ProviderTransportPhase.CONNECT)
    if _contains_errno(chain, *_NETWORK_UNREACHABLE_ERRNOS):
        return _transport("provider_network_unreachable", ProviderTransportPhase.CONNECT)
    if _contains_errno(chain, errno.ETIMEDOUT):
        return _timeout("provider_connect_timeout", ProviderTransportPhase.CONNECT)

    if _contains_type(chain, httpx.RemoteProtocolError) or _contains_httpcore_type(
        chain, "RemoteProtocolError"
    ):
        return _transport("provider_remote_protocol_error", ProviderTransportPhase.RESPONSE)
    if _contains_type(chain, httpx.WriteError) or _contains_httpcore_type(chain, "WriteError"):
        return _transport("provider_write_interrupted", ProviderTransportPhase.WRITE)
    if _contains_type(chain, httpx.ReadError) or _contains_httpcore_type(chain, "ReadError"):
        return _transport("provider_response_read_interrupted", ProviderTransportPhase.READ)
    if _contains_type(chain, httpx.ConnectError) or _contains_httpcore_type(chain, "ConnectError"):
        return _transport("provider_connect_failed", ProviderTransportPhase.CONNECT)
    if _contains_type(chain, httpx.NetworkError) or _contains_httpcore_type(chain, "NetworkError"):
        return _transport("provider_network_error", ProviderTransportPhase.TRANSPORT)
    return _transport("provider_transport_error", ProviderTransportPhase.TRANSPORT)


def _allowlisted_transport_chain(exception: Exception) -> Iterator[BaseException]:
    current: BaseException | None = exception
    seen: set[int] = set()
    for _ in range(_MAX_CHAIN_DEPTH):
        if current is None or id(current) in seen:
            return
        seen.add(id(current))
        yield current
        if not _is_allowlisted_chain_link(current):
            return
        candidate = current.__cause__ if current.__cause__ is not None else current.__context__
        if candidate is not None and not _is_allowlisted_chain_link(candidate):
            return
        current = candidate


def _is_allowlisted_chain_link(exception: BaseException) -> bool:
    return isinstance(exception, (httpx.TransportError, OSError)) or (
        type(exception).__module__ == "httpcore"
        and type(exception).__name__ in _HTTP_CORE_TRANSPORT_TYPES
    )


def _contains_type(chain: tuple[BaseException, ...], expected: type[BaseException]) -> bool:
    return any(isinstance(item, expected) for item in chain)


def _contains_httpcore_type(chain: tuple[BaseException, ...], expected: str) -> bool:
    return any(
        type(item).__module__ == "httpcore" and type(item).__name__ == expected for item in chain
    )


def _contains_errno(chain: tuple[BaseException, ...], *values: int) -> bool:
    allowed = frozenset(values)
    return any(isinstance(item, OSError) and item.errno in allowed for item in chain)


def _timeout(code: str, phase: ProviderTransportPhase) -> ProviderError:
    return ProviderError(
        ProviderErrorCategory.TIMEOUT,
        code,
        "The selected Provider request timed out",
        safe_phase=phase,
    )


def _transport(code: str, phase: ProviderTransportPhase) -> ProviderError:
    return ProviderError(
        ProviderErrorCategory.TRANSPORT_ERROR,
        code,
        "The selected Provider transport failed safely",
        safe_phase=phase,
    )
