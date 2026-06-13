# Governance Model

Governance is a separate architectural concern from orchestration.

Conceptually:

Physical Infrastructure
    -> Governance
    -> Managed Systems

Governance should remain capable of evaluating:

- trust
- authority
- policy
- incidents
- operational health

even when orchestration systems are degraded.

Governance should never be wholly dependent upon the systems it governs.
