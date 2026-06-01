#!/usr/bin/env python3
"""
setup_ddns.py — External DNS auto-update configuration (Phase 1.F.8c).

Generates configuration for keeping the hatchery's external DNS A record
pointing at the operator's dynamic WAN IP. Used when the operator has a
dynamic WAN IP and needs automatic updates.

Supported providers (via dns-lexicon except DuckDNS):
  cloudflare  — 90+ provider API via dns-lexicon
  duckdns     — Simple HTTPS GET (free subdomain; no own domain needed)
  lexicon:*   — Any dns-lexicon supported provider (namecheap, godaddy, etc.)
  null        — Static IP / manual management

Provides:
  DdnsConfig             — structured configuration
  DdnsProvider           — provider constants
  generate_ddns_config() — build from network_topology + host_identity
  render_update_script() — render update-dns.py script content
  render_systemd_timer() — render broodforge-ddns.timer unit
  render_systemd_service() — render broodforge-ddns.service unit
  config_to_dict()       — serialise for testing

Stdlib only.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------

class DdnsProvider:
    CLOUDFLARE = "cloudflare"
    DUCKDNS    = "duckdns"
    NONE       = "none"

    @staticmethod
    def is_lexicon_provider(provider: str) -> bool:
        return provider.startswith("lexicon:") or provider == DdnsProvider.CLOUDFLARE

    @staticmethod
    def all_supported() -> list[str]:
        return [
            DdnsProvider.CLOUDFLARE,
            DdnsProvider.DUCKDNS,
            DdnsProvider.NONE,
        ]


# ---------------------------------------------------------------------------
# DdnsConfig
# ---------------------------------------------------------------------------

@dataclass
class DdnsConfig:
    """Structured DDNS configuration."""

    provider:              str = DdnsProvider.NONE

    # DNS zone being managed (e.g. "example.com")
    zone:                  str = ""

    # Record to update (e.g. "hatchery" — becomes hatchery.example.com)
    record:                str = ""

    # KeePass path for API token/key
    credential_keepass_path: str = ""

    # DuckDNS-specific: subdomain (e.g. "myhatchery" → myhatchery.duckdns.org)
    duckdns_subdomain:     Optional[str] = None

    # Update interval (minutes)
    update_interval_minutes: int = 5

    # Cache file for last-known WAN IP
    cache_file:            str = "/var/lib/broodforge/last-wan-ip"

    # WAN IP detection services (tried in order)
    wan_ip_services:       list[str] = field(
        default_factory=lambda: ["https://ifconfig.me", "https://api.ipinfo.io/ip"]
    )


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_ddns_config(
    network_topology: dict,
    host_identity:    dict,
) -> DdnsConfig:
    """
    Build DdnsConfig from network_topology and host_identity dicts.

    Uses network_topology.wan_config keys:
      ddns_provider, ddns_zone, ddns_record, ddns_credential_reference
    """
    wan      = network_topology.get("wan_config") or {}
    provider = wan.get("ddns_provider") or DdnsProvider.NONE
    zone     = wan.get("ddns_zone")     or (host_identity.get("domain") or "")
    record   = wan.get("ddns_record")   or (host_identity.get("hostname") or "hatchery")
    cred_ref = wan.get("ddns_credential_reference") or ""

    duckdns_sub = None
    if provider == DdnsProvider.DUCKDNS:
        # DuckDNS subdomain: record (not zone)
        duckdns_sub = record

    return DdnsConfig(
        provider=provider,
        zone=zone,
        record=record,
        credential_keepass_path=cred_ref,
        duckdns_subdomain=duckdns_sub,
        update_interval_minutes=5,
        cache_file="/var/lib/broodforge/last-wan-ip",
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_update_script(config: DdnsConfig) -> str:
    """
    Render update-dns.py — the WAN IP detection and DNS update script.
    This script is called by the systemd timer every 5 minutes.
    """
    if config.provider == DdnsProvider.NONE:
        return """\
#!/usr/bin/env python3
# update-dns.py — DDNS disabled (provider: none)
# No DNS update configured. Manage your A record manually.
import sys
print("DDNS provider not configured — exiting.")
sys.exit(0)
"""

    if config.provider == DdnsProvider.DUCKDNS:
        return _render_duckdns_script(config)
    return _render_lexicon_script(config)


def _render_duckdns_script(config: DdnsConfig) -> str:
    subdomain = config.duckdns_subdomain or config.record
    return f"""\
#!/usr/bin/env python3
# update-dns.py — DuckDNS DDNS updater (Phase 1.F.8c)
# Called by broodforge-ddns.timer every {config.update_interval_minutes} minutes.
# Token retrieved from KeePass at: {config.credential_keepass_path}

import sys, os, json, urllib.request, urllib.error

CACHE_FILE    = "{config.cache_file}"
SUBDOMAIN     = "{subdomain}"
WAN_SERVICES  = {config.wan_ip_services!r}

def get_wan_ip():
    for svc in WAN_SERVICES:
        try:
            with urllib.request.urlopen(svc, timeout=10) as r:
                return r.read().decode().strip()
        except Exception:
            continue
    return None

def get_cached_ip():
    try:
        return open(CACHE_FILE).read().strip()
    except FileNotFoundError:
        return None

def cache_ip(ip):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    open(CACHE_FILE, "w").write(ip)

def update_duckdns(token, ip):
    url = (
        f"https://www.duckdns.org/update?domains={{SUBDOMAIN}}"
        f"&token={{token}}&ip={{ip}}&verbose=true"
    )
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode()

if __name__ == "__main__":
    token = os.environ.get("DDNS_TOKEN")
    if not token:
        print("DDNS_TOKEN not set — use KeePass to retrieve and export it.", file=sys.stderr)
        sys.exit(1)
    wan_ip = get_wan_ip()
    if not wan_ip:
        print("Could not detect WAN IP — all services failed.", file=sys.stderr)
        sys.exit(1)
    cached = get_cached_ip()
    if wan_ip == cached:
        print(f"WAN IP unchanged ({{wan_ip}}) — no update needed.")
        sys.exit(0)
    result = update_duckdns(token, wan_ip)
    if result.startswith("OK"):
        cache_ip(wan_ip)
        print(f"Updated DuckDNS {{SUBDOMAIN}} → {{wan_ip}}")
    else:
        print(f"DuckDNS update failed: {{result}}", file=sys.stderr)
        sys.exit(1)
"""


def _render_lexicon_script(config: DdnsConfig) -> str:
    provider = config.provider
    zone     = config.zone
    record   = config.record
    return f"""\
#!/usr/bin/env python3
# update-dns.py — dns-lexicon DDNS updater (Phase 1.F.8c)
# Provider: {provider}  Zone: {zone}  Record: {record}
# Called by broodforge-ddns.timer every {config.update_interval_minutes} minutes.
# Token retrieved from KeePass at: {config.credential_keepass_path}

import sys, os, subprocess, urllib.request, urllib.error

CACHE_FILE    = "{config.cache_file}"
DNS_PROVIDER  = "{provider}"
DNS_ZONE      = "{zone}"
DNS_RECORD    = "{record}"
WAN_SERVICES  = {config.wan_ip_services!r}

def get_wan_ip():
    for svc in WAN_SERVICES:
        try:
            with urllib.request.urlopen(svc, timeout=10) as r:
                return r.read().decode().strip()
        except Exception:
            continue
    return None

def get_cached_ip():
    try:
        return open(CACHE_FILE).read().strip()
    except FileNotFoundError:
        return None

def cache_ip(ip):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    open(CACHE_FILE, "w").write(ip)

def update_via_lexicon(token, ip):
    env = dict(os.environ)
    env[f"LEXICON_{{DNS_PROVIDER.upper()}}_AUTH_TOKEN"] = token
    result = subprocess.run(
        ["lexicon", DNS_PROVIDER, "update", DNS_ZONE, "A",
         "--name", DNS_RECORD, "--content", ip],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()

if __name__ == "__main__":
    token = os.environ.get("DDNS_TOKEN")
    if not token:
        print("DDNS_TOKEN not set — use KeePass to retrieve and export it.", file=sys.stderr)
        sys.exit(1)
    wan_ip = get_wan_ip()
    if not wan_ip:
        print("Could not detect WAN IP — all services failed.", file=sys.stderr)
        sys.exit(1)
    cached = get_cached_ip()
    if wan_ip == cached:
        print(f"WAN IP unchanged ({{wan_ip}}) — no update needed.")
        sys.exit(0)
    try:
        update_via_lexicon(token, wan_ip)
        cache_ip(wan_ip)
        print(f"Updated {{DNS_RECORD}}.{{DNS_ZONE}} → {{wan_ip}}")
    except RuntimeError as e:
        print(f"Lexicon update failed: {{e}}", file=sys.stderr)
        sys.exit(1)
"""


def render_systemd_timer(config: DdnsConfig) -> str:
    """Render broodforge-ddns.timer systemd unit."""
    return f"""\
[Unit]
Description=Broodforge DDNS update timer

[Timer]
OnBootSec=60s
OnUnitActiveSec={config.update_interval_minutes}min

[Install]
WantedBy=timers.target
"""


def render_systemd_service(config: DdnsConfig) -> str:
    """Render broodforge-ddns.service systemd unit."""
    return """\
[Unit]
Description=Broodforge DDNS WAN IP update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/broodforge-update-dns.py
StandardOutput=journal
StandardError=journal
"""


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def config_to_dict(config: DdnsConfig) -> dict:
    """Serialise DdnsConfig to a plain dict."""
    return {
        "provider":                config.provider,
        "zone":                    config.zone,
        "record":                  config.record,
        "credential_keepass_path": config.credential_keepass_path,
        "duckdns_subdomain":       config.duckdns_subdomain,
        "update_interval_minutes": config.update_interval_minutes,
        "cache_file":              config.cache_file,
        "wan_ip_services":         list(config.wan_ip_services),
    }
