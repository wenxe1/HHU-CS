from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.db.repositories import ResourceTaskRepository
from app.models.tutor import CodeReviewIssue, CodeReviewRecord
from app.schemas.tutor import CodeReviewRequest
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient
from app.services.rag_retrieval import retrieve_rag_context


CODE_REVIEW_RESPONSE_SCHEMA = {
    "summary": "string",
    "issues": [
        {
            "category": "compile_error|syntax_error|logic_error|boundary_error|complexity|style",
            "severity": "info|warning|error",
            "title": "string",
            "detail": "string",
            "suggestion": "string",
            "line": "integer|null",
        }
    ],
    "suggestions": ["string"],
    "next_steps": ["string"],
}


class CodeReviewService:
    def __init__(
        self,
        repository: ResourceTaskRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def review(self, request: CodeReviewRequest) -> dict[str, Any]:
        rag_context = []
        if request.course_id:
            rag_context = await retrieve_rag_context(
                repository=self._repository,
                ai_client=self._ai_client,
                course_id=request.course_id,
                query=f"{request.knowledge_point_id or ''} {request.language} 代码纠错",
            )
        generated = await self._generate_review(request, rag_context)
        issues = self._validate_issues(generated.get("issues", []))
        record = CodeReviewRecord(
            record_id=str(uuid4()),
            user_id=request.user_id,
            language=request.language,
            code=request.code,
            course_id=request.course_id,
            knowledge_point_id=request.knowledge_point_id,
            error_message=request.error_message,
            summary=generated["summary"],
            issues=issues,
            suggestions=generated["suggestions"],
        )

        await self._repository.save_code_review_record(record)

        return {
            "record_id": record.record_id,
            "language": record.language,
            "summary": record.summary,
            "issues": [issue.model_dump(mode="json") for issue in record.issues],
            "suggestions": record.suggestions,
            "next_steps": generated["next_steps"],
        }

    async def _generate_review(
        self,
        request: CodeReviewRequest,
        rag_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system_prompt = (
            "你是 EduAgent Studio 的 Code Review Agent。"
            "你必须真实分析学生提交的 C++ 或 Python 代码，结合错误信息、知识点和课程资料，"
            "指出编译/语法、逻辑、边界条件和复杂度问题。不要基于简单关键词猜测。"
        )
        user_prompt = (
            f"user_id: {request.user_id}\n"
            f"course_id: {request.course_id}\n"
            f"knowledge_point_id: {request.knowledge_point_id}\n"
            f"language: {request.language}\n"
            f"error_message: {request.error_message}\n"
            f"code:\n{request.code}\n"
            f"retrieved_context: {rag_context}\n"
            "请输出结构化代码评审。"
        )
        generated = await self._ai_client.generate_json(
            agent_name="Code Review Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=CODE_REVIEW_RESPONSE_SCHEMA,
            use_reasoning=True,
        )
        self._require_keys(
            generated,
            ["summary", "issues", "suggestions", "next_steps"],
        )
        return generated

    def _validate_issues(self, items: list[dict[str, Any]]) -> list[CodeReviewIssue]:
        try:
            return [CodeReviewIssue.model_validate(item) for item in items]
        except ValidationError as exc:
            raise AIServiceError("Code Review Agent returned invalid issues") from exc

    def _require_keys(self, payload: dict[str, Any], keys: list[str]) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise AIServiceError(f"Code Review Agent response missing keys: {missing}")
