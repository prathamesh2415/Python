from __future__ import annotations

import logging
import os
import ssl
from functools import lru_cache

import httpx

logger = logging.getLogger(__name__)


def configure_ssl_env() -> str | None:
    """Point Python/OpenSSL at a known CA bundle (fixes many Windows SSL failures)."""
    try:
        import certifi

        ca_path = certifi.where()
    except Exception as exc:  # noqa: BLE001
        logger.warning("certifi unavailable (%s)", exc)
        return None

    os.environ.setdefault("SSL_CERT_FILE", ca_path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_path)
    os.environ.setdefault("CURL_CA_BUNDLE", ca_path)
    return ca_path


@lru_cache(maxsize=1)
def ssl_verify_setting() -> bool | str:
    """Return httpx/ssl verify setting.

    - Default: certifi CA bundle path
    - FACELESS_SSL_INSECURE=1: disable verify (last resort for corporate SSL inspection)
    """
    insecure = os.getenv("FACELESS_SSL_INSECURE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if insecure:
        logger.warning(
            "SSL verification disabled via FACELESS_SSL_INSECURE=1 "
            "(use only on trusted networks)"
        )
        return False

    ca_path = configure_ssl_env()
    if ca_path:
        return ca_path
    return True


def make_async_client(timeout: float = 90.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, verify=ssl_verify_setting())


def make_ssl_context() -> ssl.SSLContext | bool:
    verify = ssl_verify_setting()
    if verify is False:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if isinstance(verify, str):
        return ssl.create_default_context(cafile=verify)
    return ssl.create_default_context()
