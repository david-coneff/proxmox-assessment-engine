#!/usr/bin/env bash
# sync-cert-to-k8s.sh — Sync TLS certificate to Kubernetes secrets.
#
# NOT IMPLEMENTED: this script is registered as a remediation action type in
# remediation_executor.py but the implementation has not yet been written.
# It deliberately exits 1 so that the remediation engine records a FAILED
# execution rather than silently claiming success with no actual TLS sync.
#
# TODO: implement using:
#   kubectl create secret tls <name> --cert=fullchain.pem --key=privkey.pem \
#     -n <namespace> --dry-run=client -o yaml | kubectl apply -f -
# or via cert-manager annotation sync once the k8s secret management pattern
# is decided. Until then, operators must manually sync TLS certs to k8s.

set -euo pipefail

echo "[sync-cert-to-k8s] ERROR: Not yet implemented — TLS certificate was NOT synced." >&2
echo "[sync-cert-to-k8s] Sync the certificate to k8s manually:" >&2
echo "[sync-cert-to-k8s]   kubectl create secret tls <name> \\" >&2
echo "[sync-cert-to-k8s]     --cert=fullchain.pem --key=privkey.pem -n <namespace>" >&2
exit 1
