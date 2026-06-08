# Broodforge Feature & Design-Intent History

**Trailing history of features and design intents** requested over time, newest cycle
last. Each entry records its **origin** (USER-REQUESTED vs. GAP-FILL — devised to fill
an under-specified idea), **status**, and **verification depth**:

- `static` — grep/pattern checks only
- `cli-probe` — `--help` / flag-existence checks
- `smoke` — ran the code path with synthetic/mocked inputs
- `unit` — covered by the pytest suite
- `deep-arch` — full execution pathway traced for gaps
- `user-tested` — confirmed by a real user on hardware (record version + feedback)

Timestamps are `YYYY-MM-DD_HH_MM_SS` UTC.

---

**Cycle: 2026-06-04_12_37_46 UTC**

## Interactive HTML documentation toolkit (`proxmox-bootstrap/md_to_html.py`)

| Feature | Origin | Status | Verification |
|---|---|---|---|
| Markdown → themed self-contained HTML | GAP-FILL (README/ROADMAP/etc. needed HTML twins) | Implemented | smoke (structure asserts on every generated doc) |
| Light/dark theme toggle (persisted) | USER-REQUESTED | Implemented | smoke (toggle + `body.light` present in output) |
| Per-code-block Copy buttons | USER-REQUESTED | Implemented | smoke |
| Live-templated commands (`{{VAR}}` → Parameters panel, live rewrite) | USER-REQUESTED | Implemented | smoke (param inputs + `.tpl` slots in drill HTML) |
| Note fields (`@field`/`@area`) + auto Session Notes | USER-REQUESTED | Implemented | smoke |
| File **Attachments** + **Export** to timestamped ZIP (`Title_YYYY_MM_DD_HH_MM_SS.zip`) | USER-REQUESTED | Implemented | smoke + **format-validated**: ported the JS CRC32/ZIP builder to Python and confirmed `zipfile` reads + CRC-checks the output |
| Theme toggle injected into hand-authored HTML (`inject_html_theme.py`) | GAP-FILL | Implemented | smoke (markers + balanced tags) |
| `--collapsible` (## sections → `<details>`) | GAP-FILL (FEATURE-HISTORY needs collapsible per memory) | Implemented | smoke |

> **Not yet user-tested.** The export/attachments + live-template UX has only been
> validated structurally and (for the ZIP) by format round-trip. A real browser test
> by the user would raise confidence to `user-tested`.

## Forge / spawn / phoenix workflow completeness (audit-driven)

| Feature | Origin | Status | Verification |
|---|---|---|---|
| Forge package self-bundles library code | GAP-FILL (docs implied it) | Implemented | smoke (tarball contents) + unit |
| Dashboard secret redaction on unauth GET | GAP-FILL (security) | Implemented | smoke (mask + non-mutation) + unit |
| `validate-spawn.py` conflict re-validator CLI + bundling | GAP-FILL | Implemented | smoke (collision→exit1, clean→exit0) |
| Phoenix playbook generation entry point (`phoenix-planner --state`) | GAP-FILL (missing step) | Implemented | smoke (generate→assemble→package) |
| `engine.py --set-timezone` (AD-045) | USER-REQUESTED (architecture decision) | Implemented | smoke |
| `spawn_hardware_discovery.py` CLI + sshpass password auth | GAP-FILL (documented step had no CLI) | Implemented | cli-probe + smoke (mocked runner) |
| `setup_ddns.py` CLI (both forge + manual forms) | GAP-FILL | Implemented | smoke (both forms, units written) |
| `init-bootstrap-state.py` manifest-seeded non-interactive init | GAP-FILL (would hang forge.sh) | Implemented | smoke (stdin-closed, seeded) |
| `setup_dnsmasq/headscale/tls.py` CLIs (forge phase-03) | GAP-FILL (were library-only no-ops) | Implemented | smoke (each writes a real config; dnsmasq `hostname` field bug also fixed) |
| Forge OpenTofu VM modules + Ansible inventory generation | GAP-FILL | **Not implemented** — deploy-to-hardware milestone | deep-arch (gap confirmed); documented in FORGING.md |

## Documentation integrity

| Feature | Origin | Status | Verification |
|---|---|---|---|
| All documented `python3` commands resolve + flags implemented | USER-REQUESTED (no broken steps) | Implemented | deep-arch (import-aware flag cross-reference: 0 mismatches) |
| Durable `DESIGN-HISTORY.md` replacing versioned review churn | USER-REQUESTED | Implemented | static |
| `AUDIT-FINDINGS.md` (this trailing audit log) | USER-REQUESTED | Implemented | n/a |
| `FEATURE-HISTORY.md` (+ collapsible HTML) | USER-REQUESTED | Implemented | n/a |

---

**Cycle: 2026-06-08_04_54_51 UTC**

## Security & documentation: MFA-by-default, collapsible roadmap

| Feature | Origin | Status | Verification |
|---|---|---|---|
| KeePass unlock gate now defaults to second-factor (`mfa_method` / `--mfa` default flips `"none"` → `"totp"`; AD-058) | USER-REQUESTED ("for high level functions of any kind, we should be requiring 2nd factor authentication as a default, not just a password") | Implemented | unit (`test_keepass_mfa.py`, 49 passed; `test_mfa_method_field_default` updated to assert `"totp"`) |
| MFA method constrained to authenticator-app TOTP or YubiKey only — SMS/email OTP deliberately never offered | USER-REQUESTED ("the 2nd factor method should be limited to TOTP-authenticator or yubikey, not SMS based TOTP or email-based TOTP since this have greater vulnerability to being hacked") | Implemented (pre-existing `keepass_mfa.py` already had no SMS/email path; default flip + AD-058 make the constraint the documented baseline) | unit + static (grep confirms no SMS/email OTP code path exists anywhere in `keepass_mfa.py` / `forge_keepass_init.py`) |

---

**Cycle: 2026-06-08_12_36_41 UTC**

## AD-058 follow-up: MFA method now seen and confirmed at forge time (guided-setup gap closed)

The prior cycle named one open gap: the `"totp"` MFA default was *inherited
silently* — `guided_setup.py`/`forge_planner.py` didn't surface it for operator
confirmation. This cycle closes that gap end-to-end (guided setup → forge
manifest → KeePass init), completing work a prior session had left mid-flight
(uncommitted edits found already started in the working tree on resume).

| Feature | Origin | Status | Verification |
|---|---|---|---|
| `security.mfa_method` added to the guided-setup `security` group (suggest → `"totp"`; `check_conflicts` validates against `{none, totp, yubikey}`, rejects SMS/email-style values, warns on `"none"` as an explicit AD-058 opt-out) | GAP-FILL (closes the named AD-058 follow-up — "seen and confirmed," not silently inherited) | Implemented | unit (`test_guided_setup.py`: suggest + 4 new `check_conflicts` cases) |
| `build_forge_manifest()` writes `keepass_config.mfa_method` from the guided session's `security.mfa_method` choice when present, else the `"totp"` default | GAP-FILL | Implemented | unit (`test_forge_planner.py::test_mfa_method_defaults_to_totp`, `::test_mfa_method_from_guided_session`) |
| `generate_keepass_init_config()` reads `forge_manifest["keepass_config"]["mfa_method"]` and threads it into the returned `KeePassInitConfig` (was computed but not wired through — completed the in-flight edit) | GAP-FILL | Implemented | unit (full `keepass`/`mfa`/`forge_planner`/`guided_setup` sweep: 363 passed) |
| Fixed `verify_trust()` (`federation_state.py`) comparing `relationship.is_expired` (real wall-clock `datetime.now()`) against an injected `now_fn` — caused `test_phase19_federation.py::test_expiring_soon_still_valid` to flip red the moment real UTC time passed the fixture's fixed "soon" expiry date | GAP-FILL (latent bug surfaced by the calendar advancing past the test's fixed fixture date — same class of issue PAP/audit work has repeatedly flagged: real-time calls inside logic meant to be driven by injected clocks) | Implemented | unit (`test_phase19_federation.py`: 51 passed; full suite: 3844 passed) |

> Full suite: **3844 passed** (was 3843 + 1 pre-existing failure from the
> `federation_state.py` clock bug above — both now green).
| `ROADMAP.html` regenerated with collapsible (`<details>`/`<summary>`) sections via `md_to_html.py --collapsible`, matching `FEATURE-HISTORY.html`'s pattern | USER-REQUESTED ("broodforge's roadmap should be revised to use collapsible sections, it's quite lengthy at this point") | Implemented | smoke (`<details>`/`</details>` balanced: 9/9; `test_meta_doc_sync.py` passes) — regeneration also closed a content-drift gap the prior hand-sync missed (three draft-sketch `<h3>` sections existed in `ROADMAP.md` but were absent from the old `ROADMAP.html`) |
