# Domain Model

Objects:

TrustSubject
TrustAssessment
TrustEvidence
TrustRelationship
Secret
SecretVersion
SecretLease
BrokerDecision
AuditRecord

Relationships:

TrustEvidence -> TrustAssessment

TrustAssessment -> TrustSubject

SecretLease -> Secret

BrokerDecision -> TrustAssessment

All objects are event-backed and auditable.
