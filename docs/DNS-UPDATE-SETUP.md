# External DNS Setup — Overview

**Document created:** 2026-05-31
**Review by:** 2027-05-31

This document is an index. Detailed setup guides are in the dedicated files linked below.

---

## Which guide applies to you?

| Your situation | Go to |
|---|---|
| You have your own domain (any registrar, including Squarespace) | [CLOUDFLARE-SETUP.md](CLOUDFLARE-SETUP.md) |
| You want the simplest free option with no own domain | [DUCKDNS-SETUP.md](DUCKDNS-SETUP.md) |
| You have another registrar with a supported API | [CLOUDFLARE-SETUP.md](CLOUDFLARE-SETUP.md) (Cloudflare delegation is still recommended) or see dns-lexicon section below |

---

## Summary comparison

| Feature | Cloudflare | DuckDNS |
|---|---|---|
| Own domain required | Yes (but any registrar works — just delegate NS) | No — free `*.duckdns.org` subdomain |
| DDNS tool | dns-lexicon | Direct HTTPS GET (no tool needed) |
| Let's Encrypt tool | certbot (official plugin) | acme.sh (built-in DuckDNS support) |
| Wildcard certs | Yes — `*.home.example.com` | Yes — `*.myhatchery.duckdns.org` |
| cert-manager (k3s) | Native ClusterIssuer DNS-01 | Manual cert sync to k8s secret |
| Squarespace compatible | Yes — delegate nameservers to Cloudflare | N/A |

---

## Squarespace note

Squarespace has no DNS API. You cannot auto-update DNS records or use DNS-01 challenges
directly through Squarespace. The standard path is to delegate DNS management to
Cloudflare (change nameservers in Squarespace → "Use Custom Nameservers"). Your
domain stays registered at Squarespace; Cloudflare handles all DNS.

See [CLOUDFLARE-SETUP.md](CLOUDFLARE-SETUP.md) Step 1.2–1.3 for the nameserver delegation walkthrough.

---

## Other registrars via dns-lexicon

If you have your own domain at a registrar not mentioned above, dns-lexicon supports
90+ providers. Check if yours is listed:

```bash
pip install dns-lexicon
lexicon --help   # lists all supported providers
```

Or visit: https://dns-lexicon.github.io/dns-lexicon/providers_options.html

The Cloudflare guide applies conceptually — substitute `cloudflare` with your provider
name in the lexicon commands. For Let's Encrypt, certbot has DNS plugins for many
registrars: `apt search python3-certbot-dns` to see what's available in your apt repo.

---

## Tools used (and one to avoid)

| Tool | Status | Used for |
|---|---|---|
| dns-lexicon | ✓ Active (v3.25.2, May 2026) | Cloudflare DDNS updates, 90+ other providers |
| acme.sh | ✓ Active | DuckDNS Let's Encrypt DNS-01 |
| certbot | ✓ Active | Cloudflare Let's Encrypt DNS-01 |
| inadyn | ✗ Archived Oct 2025 | Do not use |
| ddclient | ✓ Active | Alternative to dns-lexicon for some providers |

---

## Caddy as an alternative to certbot/acme.sh + nginx

[Caddy](https://caddyserver.com) is a web server that handles TLS certificate
issuance and renewal automatically with almost zero configuration. It supports
ACME DNS-01 challenges via provider plugins and can serve as both the reverse proxy
(replacing nginx) and the cert manager (replacing certbot/acme.sh) in one process.

**When to consider Caddy:**
- You want the absolute minimum configuration for TLS
- You are already planning to use Caddy as the host-level reverse proxy for Forgejo
  and other pre-k3s services

**When not to use Caddy:**
- When Headscale is the primary service needing TLS (Headscale has its own TLS config
  and does not sit behind a reverse proxy in the standard broodforge setup)
- When you need the same cert for both host services and k3s workloads (certbot/acme.sh
  gives you more control over the cert lifecycle)

**Caddy + Cloudflare example (Caddyfile):**
```
{
  acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
}

forgejo.home.example.com {
  reverse_proxy localhost:3000
  # Caddy automatically obtains and renews the cert via Cloudflare DNS-01
}
```

For Headscale, use certbot or acme.sh directly (Headscale terminates TLS itself;
it does not sit behind Caddy). Caddy is most useful for services that proxy through
a web server rather than handling their own TLS.

Full Caddy documentation: [caddyserver.com/docs](https://caddyserver.com/docs)
Caddy Cloudflare DNS plugin: [github.com/caddy-dns/cloudflare](https://github.com/caddy-dns/cloudflare)

---

## Keeping these documents current

DNS provider UIs, APIs, and tools change. Each guide has its own review date at the top.
If you find a step that no longer matches, update the relevant file and change the date.

The most likely things to change:
- Squarespace dashboard navigation (changes frequently)
- Cloudflare dashboard navigation
- acme.sh DNS provider API names (run `acme.sh --list-dns` for current list)
- dns-lexicon provider names (run `lexicon --help` for current list)
