# Trust State Machine

UNKNOWN
-> EVALUATING
-> TRUSTED
-> RESTRICTED
-> REVOKED
-> RECOVERING

# Lease State Machine

REQUESTED
-> EVALUATING
-> GRANTED
-> ACTIVE
-> COMPLETED

Alternative:

DENIED
REVOKED
EXPIRED

All transitions generate events.
