from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.resource import AuditStatus


RiskLevel = Literal["low", "medium", "high"]


class AuditIssue(BaseModel):
    category: str
    severity: RiskLevel
    detail: str
    suggestion: str


class ContentAudit(BaseModel):
    audit_id: str
    resource_id: str
    status: AuditStatus
    risk_level: RiskLevel
    issues: list[AuditIssue] = Field(default_factory=list)
    citations: list[dict[str, str]] = Field(default_factory=list)
    hallucination_checks: list[str] = Field(default_factory=list)
    auditor_agent: str = "Safety Agent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
