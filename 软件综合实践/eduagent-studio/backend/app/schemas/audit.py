from pydantic import BaseModel


class AuditResourceRequest(BaseModel):
    auditor_id: str | None = None
    strictness: str = "standard"


class AuditIssueResponse(BaseModel):
    category: str
    severity: str
    detail: str
    suggestion: str


class AuditResourceResult(BaseModel):
    audit_id: str
    resource_id: str
    status: str
    risk_level: str
    issues: list[AuditIssueResponse]
    citations: list[dict[str, str]]
    hallucination_checks: list[str]
    auditor_agent: str
    created_at: str
