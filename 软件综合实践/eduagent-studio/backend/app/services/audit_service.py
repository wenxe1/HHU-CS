from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.db.repositories import ResourceTaskRepository
from app.models.audit import AuditIssue, ContentAudit
from app.models.resource import AuditStatus
from app.schemas.audit import AuditResourceRequest
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient
from app.services.rag_retrieval import retrieve_rag_context


AUDIT_RESPONSE_SCHEMA = {
    "status": "approved|rejected",
    "risk_level": "low|medium|high",
    "issues": [
        {
            "category": "safety|factuality|quality|copyright",
            "severity": "low|medium|high",
            "detail": "string",
            "suggestion": "string",
        }
    ],
    "citations": [{"source_type": "string", "source_id": "string", "title": "string"}],
    "hallucination_checks": ["string"],
}


class AuditService:
    def __init__(
        self,
        repository: ResourceTaskRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def audit_resource(
        self,
        resource_id: str,
        request: AuditResourceRequest,
    ) -> dict[str, Any] | None:
        resource = await self._repository.get_resource(resource_id)
        if resource is None:
            return None

        rag_context = await retrieve_rag_context(
            repository=self._repository,
            ai_client=self._ai_client,
            course_id=resource.course_id,
            query=f"{resource.knowledge_point_id} {resource.title} 内容审核",
        )
        generated = await self._generate_audit(
            resource.model_dump(mode="json"),
            request,
            rag_context,
        )
        issues = self._validate_issues(generated.get("issues", []))
        status = self._validate_status(generated["status"])
        audit = ContentAudit(
            audit_id=str(uuid4()),
            resource_id=resource.resource_id,
            status=status,
            risk_level=generated["risk_level"],
            issues=issues,
            citations=generated["citations"],
            hallucination_checks=generated["hallucination_checks"],
        )

        resource.audit_status = status
        resource.updated_at = datetime.now(UTC)
        await self._repository.update_resource(resource)
        await self._repository.save_content_audit(audit)

        return audit.model_dump(mode="json")

    async def _generate_audit(
        self,
        resource_payload: dict[str, Any],
        request: AuditResourceRequest,
        rag_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system_prompt = (
            "你是 EduAgent Studio 的 Safety Agent。"
            "你必须对学习资源做安全、事实性、质量和引用依据审核。"
            "审核必须基于资源内容和检索到的课程资料，不能用关键词规则替代判断。"
        )
        user_prompt = (
            f"auditor_id: {request.auditor_id}\n"
            f"strictness: {request.strictness}\n"
            f"resource: {resource_payload}\n"
            f"retrieved_context: {rag_context}\n"
            "请输出结构化审核结果。"
        )
        generated = await self._ai_client.generate_json(
            agent_name="Safety Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=AUDIT_RESPONSE_SCHEMA,
            use_reasoning=True,
        )
        self._require_keys(
            generated,
            ["status", "risk_level", "issues", "citations", "hallucination_checks"],
        )
        return generated

    def _validate_issues(self, items: list[dict[str, Any]]) -> list[AuditIssue]:
        try:
            return [AuditIssue.model_validate(item) for item in items]
        except ValidationError as exc:
            raise AIServiceError("Safety Agent returned invalid issues") from exc

    def _validate_status(self, value: str) -> AuditStatus:
        if value not in {"pending", "approved", "rejected"}:
            raise AIServiceError(f"Safety Agent returned invalid status: {value}")
        return value

    def _require_keys(self, payload: dict[str, Any], keys: list[str]) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise AIServiceError(f"Safety Agent response missing keys: {missing}")
