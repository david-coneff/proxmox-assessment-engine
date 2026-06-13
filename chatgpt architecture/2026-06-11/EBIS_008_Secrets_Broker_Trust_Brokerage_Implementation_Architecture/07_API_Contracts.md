Trust API:

GET /trust/{subject_id}
GET /trust/{subject_id}/evidence
POST /trust/review

Secrets API:

POST /leases
GET /leases/{lease_id}
POST /leases/{lease_id}/revoke
POST /secrets/{secret_id}/rotate

Rules:

- Every write emits events.
- Every revocation emits events.
- No secret disclosure without lease authorization.
