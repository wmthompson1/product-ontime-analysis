"""Arango environment config helper.

Provides a single function `load_arango_config()` which prefers `ARANGO_*` env
variables but falls back to `DATABASE_*` variants for a safe rollout.

Usage:
    from app.arango_config import load_arango_config
    cfg = load_arango_config()
    host = cfg['host']
    url = cfg.get('url')
"""
from urllib.parse import urlparse
import os
from typing import Dict, Optional


def _split_host_port(host_value: str) -> (str, Optional[int]):
    if not host_value:
        return None, None
    # accept forms: http://host:port or host:port or host
    try:
        parsed = urlparse(host_value)
        if parsed.scheme and parsed.hostname:
            return parsed.hostname, (parsed.port or None)
    except Exception:
        pass
    if ':' in host_value:
        h, p = host_value.split(':', 1)
        try:
            return h, int(p)
        except ValueError:
            return host_value, None
    return host_value, None


def load_arango_config(env: Dict[str, str] = None) -> Dict[str, Optional[str]]:
    """Load Arango config from environment with DATABASE_* fallbacks.

    Returns dict with keys: host, port, user, password, url, db
    """
    env = env or os.environ

    # Prefer ARANGO_* then fall back to DATABASE_*
    url = env.get('ARANGO_URL') or env.get('DATABASE_URL') or env.get('DATABASE_HOST')

    host = env.get('ARANGO_HOST') or env.get('DATABASE_HOST')
    port = env.get('ARANGO_PORT') or env.get('DATABASE_PORT')
    user = env.get('ARANGO_USER') or env.get('DATABASE_USERNAME') or env.get('DATABASE_USER')
    password = env.get('ARANGO_ROOT_PASSWORD') or env.get('ARANGO_PASSWORD') or env.get('DATABASE_PASSWORD')
    db = env.get('ARANGO_DB') or env.get('DATABASE_NAME')

    # normalize host:port if url provided in various formats
    if url and (not host or not port):
        # try parse ARANGO_URL like http://root:pass@host:8529
        try:
            p = urlparse(url)
            if p.hostname:
                host = host or p.hostname
            if p.port:
                port = port or str(p.port)
            if p.username:
                user = user or p.username
            if p.password:
                password = password or p.password
        except Exception:
            pass

    # final host/port split if host includes port
    if host and (not port):
        h, p = _split_host_port(host)
        if p:
            host = h
            port = str(p)

    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'url': url,
        'db': db,
    }


if __name__ == '__main__':
    import json
    print(json.dumps(load_arango_config(), indent=2))
