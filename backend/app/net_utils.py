"""Network utilities to ensure reliable outbound connectivity on dual-stack hosts."""

import logging
import socket

logger = logging.getLogger(__name__)

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=socket.AF_UNSPEC, type=0, proto=0, flags=0):
    """Prefer IPv4 addresses when family is AF_UNSPEC to avoid hangs on broken IPv6 networks."""
    if family == socket.AF_UNSPEC:
        try:
            res = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            if res:
                return res
        except socket.gaierror:
            pass
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


def patch_ipv4_preference() -> None:
    """Apply socket.getaddrinfo patch if not already applied."""
    if socket.getaddrinfo != _ipv4_first_getaddrinfo:
        socket.getaddrinfo = _ipv4_first_getaddrinfo
        logger.info("[NET] IPv4 resolution preference applied.")
