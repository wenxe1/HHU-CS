import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db.repositories import ResourceTaskRepository
from app.models.tutor import TutorMessage, TutorSession
from app.schemas.tutor import TutorAskRequest
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient
from app.services.rag_retrieval import retrieve_rag_context


TUTOR_RESPONSE_SCHEMA = {
    "answer": "string",
    "guidance_steps": ["string"],
    "follow_up_questions": ["string"],
    "personalization": {
        "agent": "Tutor Agent",
        "reasoning_basis": ["string"],
        "evidence_gap": "string|null",
    },
}

REASONING_QUESTION_MARKERS = (
    "为什么",
    "证明",
    "推导",
    "分析",
    "复杂度",
    "优化",
    "调试",
    "报错",
    "错误",
    "代码",
    "why",
    "prove",
    "proof",
    "derive",
    "analyze",
    "complexity",
    "optimize",
    "debug",
    "error",
    "code",
)

SOURCE_GROUNDED_QUESTION_MARKERS = (
    "这份",
    "这些",
    "资料",
    "来源",
    "文档",
    "材料",
    "上传",
    "根据",
    "基于",
    "总结",
    "整理",
    "本章",
    "本节",
    "笔记",
    "课件",
    "讲义",
    "当前",
    "上述",
    "this document",
    "these materials",
    "source",
    "uploaded",
    "according to",
    "based on",
    "summarize",
    "notes",
    "material",
)

TUTOR_STREAM_IDLE_TIMEOUT_SECONDS = 90.0
RECENT_TUTOR_HISTORY_WINDOW = 12


class TutorService:
    def __init__(
        self,
        repository: ResourceTaskRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def ask(self, request: TutorAskRequest) -> dict[str, Any]:
        if not request.course_id:
            generated = await self._generate_plain_chat_answer(request)
            return await self._persist_result(request, generated, [])

        rag_context = await self._retrieve_context(request)
        needs_source_context = _needs_source_context(request)
        if needs_source_context and not rag_context:
            generated = _source_gap_response()
        else:
            generated = await self._generate_answer(
                request,
                rag_context,
                needs_source_context,
            )

        return await self._persist_result(request, generated, rag_context)

    async def stream_ask(
        self,
        request: TutorAskRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        rag_context = await self._retrieve_context(request)
        needs_source_context = _needs_source_context(request) if request.course_id else False
        if request.course_id and needs_source_context and not rag_context:
            generated = _source_gap_response()
            yield {"type": "delta", "delta": generated["answer"]}
        else:
            system_prompt, user_prompt = self._answer_prompts(
                request,
                rag_context,
                needs_source_context,
            )
            answer_parts: list[str] = []
            stream = self._ai_client.stream_text(
                agent_name="Tutor Agent",
                system_prompt=(
                    f"{system_prompt} 流式回答时仅输出回答正文，不要输出 JSON。"
                ),
                user_prompt=f"{user_prompt}\n请直接输出面向学生的回答正文。",
                use_reasoning=_needs_reasoning(request),
            )
            while True:
                try:
                    async with asyncio.timeout(TUTOR_STREAM_IDLE_TIMEOUT_SECONDS):
                        delta = await anext(stream)
                except StopAsyncIteration:
                    break
                except TimeoutError as exc:
                    raise AIServiceError("Tutor Agent AI stream idle timed out") from exc
                answer_parts.append(delta)
                yield {"type": "delta", "delta": delta}

            generated = {
                "answer": "".join(answer_parts),
                "guidance_steps": [],
                "follow_up_questions": [],
                "personalization": {
                    "agent": "Tutor Agent",
                    "reasoning_basis": ["streaming", "rag" if rag_context else "general"],
                    "evidence_gap": None,
                },
            }

        result = await self._persist_result(request, generated, rag_context)
        yield {"type": "done", "data": result}

    async def _retrieve_context(
        self,
        request: TutorAskRequest,
    ) -> list[dict[str, Any]]:
        if not request.course_id:
            return []
        try:
            return await retrieve_rag_context(
                repository=self._repository,
                ai_client=self._ai_client,
                course_id=request.course_id,
                query=f"{request.knowledge_point_id or ''} {request.question}",
                user_id=request.user_id,
                notebook_id=request.notebook_id or request.course_id,
                document_ids=request.source_document_ids,
            )
        except Exception:
            return []

    async def _persist_result(
        self,
        request: TutorAskRequest,
        generated: dict[str, Any],
        rag_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        session_id = str(uuid4())

        session = TutorSession(
            session_id=session_id,
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=request.notebook_id,
            visit_id=request.visit_id,
            knowledge_point_id=request.knowledge_point_id,
            question=request.question,
            updated_at=datetime.now(UTC),
        )
        messages = [
            TutorMessage(
                message_id=str(uuid4()),
                session_id=session_id,
                role="user",
                content=request.question,
                metadata={"code_snippet": request.code_snippet},
            ),
            TutorMessage(
                message_id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content=generated["answer"],
                metadata={
                    "agent": "Tutor Agent",
                    "rag_context": rag_context,
                    "notebook_id": request.notebook_id or request.course_id,
                    "visit_id": request.visit_id,
                    "source_document_ids": request.source_document_ids,
                },
            ),
        ]

        await self._repository.save_tutor_session(session)
        await self._repository.save_tutor_messages(messages)
        if request.course_id:
            await self._repository.trim_tutor_history(
                user_id=request.user_id,
                course_id=request.course_id,
                notebook_id=request.notebook_id,
                keep=RECENT_TUTOR_HISTORY_WINDOW,
            )

        return {
            "session_id": session_id,
            "answer": generated["answer"],
            "guidance_steps": generated["guidance_steps"],
            "follow_up_questions": generated["follow_up_questions"],
            "citations": _build_citations(rag_context),
            "personalization": {
                **generated["personalization"],
                "agent": "Tutor Agent",
                "user_id": request.user_id,
                "course_id": request.course_id,
                "notebook_id": request.notebook_id or request.course_id,
                "visit_id": request.visit_id,
                "knowledge_point_id": request.knowledge_point_id,
            },
        }

    async def delete_history(
        self,
        user_id: str,
        course_id: str | None = None,
        notebook_id: str | None = None,
        visit_id: str | None = None,
    ) -> dict[str, Any]:
        deleted_count = await self._repository.delete_tutor_history(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            visit_id=visit_id,
        )
        return {"deleted": True, "deleted_sessions": deleted_count}

    async def _generate_plain_chat_answer(
        self,
        request: TutorAskRequest,
    ) -> dict[str, Any]:
        learning_context = []
        if request.course_name:
            learning_context.append(f"当前课程：{request.course_name}")
        if request.knowledge_point_name or request.knowledge_point_id:
            knowledge_point = request.knowledge_point_name or request.knowledge_point_id
            learning_context.append(f"当前选中的知识点：{knowledge_point}")

        learning_context_prompt = "\n".join(learning_context) or "当前未选择课程或知识点"
        answer_parts: list[str] = []
        try:
            async with asyncio.timeout(28.0):
                async for delta in self._ai_client.stream_text(
                    agent_name="Tutor Agent",
                    system_prompt=(
                        "你是 EduAgent Studio 的 AI 学习助手。"
                        "这是纯 Chat 对话，不检索课程资料。"
                        "以下学习上下文来自用户界面当前选择，必须直接用于回答：\n"
                        f"{learning_context_prompt}\n"
                        "用户提到‘这个课程’或‘这个知识点’时，指的就是上述上下文，"
                        "不要再询问具体课程或知识点是什么。"
                        "回答默认保持凝练：先直接给结论，再用不超过 3 个要点补充必要解释；"
                        "除非用户明确要求详细展开，否则正文控制在 300 个中文字符以内，"
                        "不要复述问题，不写客套开场或重复总结。"
                        "直接回答用户问题，不要输出 JSON，不要声称已经读取或检索了资料。"
                    ),
                    user_prompt=f"用户问题：{request.question}",
                    use_reasoning=_needs_reasoning(request),
                ):
                    answer_parts.append(delta)
        except TimeoutError as exc:
            raise AIServiceError("Tutor Agent AI call timed out") from exc

        answer = "".join(answer_parts).strip()
        if not answer:
            raise AIServiceError("Tutor Agent returned empty content")

        return {
            "answer": answer,
            "guidance_steps": [],
            "follow_up_questions": [],
            "personalization": {
                "agent": "Tutor Agent",
                "reasoning_basis": ["plain_chat"],
                "evidence_gap": None,
            },
        }

    async def _generate_answer(
        self,
        request: TutorAskRequest,
        rag_context: list[dict[str, Any]],
        needs_source_context: bool,
    ) -> dict[str, Any]:
        system_prompt, user_prompt = self._answer_prompts(
            request,
            rag_context,
            needs_source_context,
        )
        try:
            generated = await asyncio.wait_for(
                self._ai_client.generate_json(
                    agent_name="Tutor Agent",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=TUTOR_RESPONSE_SCHEMA,
                    use_reasoning=_needs_reasoning(request),
                ),
                timeout=28.0,
            )
        except asyncio.TimeoutError as exc:
            raise AIServiceError("Tutor Agent AI call timed out") from exc
        self._require_keys(
            generated,
            ["answer", "guidance_steps", "follow_up_questions", "personalization"],
        )
        return generated

    def _answer_prompts(
        self,
        request: TutorAskRequest,
        rag_context: list[dict[str, Any]],
        needs_source_context: bool,
    ) -> tuple[str, str]:
        system_prompt = (
            "你是 EduAgent Studio 的 Tutor Agent。"
            "你必须结合当前问题、代码片段和检索到的课程资料进行辅导。"
            "不要直接替学生完成所有答案，要给出分步引导、追问和证据依据。"
            "如果 retrieved_context 不为空，回答要尽量基于这些片段，"
            "并使用 [来源标题#片段序号] 形式标注依据。"
            "如果问题明显要求基于当前来源回答但 retrieved_context 为空，"
            "必须说明当前来源范围内资料不足，不能编造。"
            "如果问题不依赖来源，可以使用通用知识回答。"
        )
        user_prompt = (
            f"user_id: {request.user_id}\n"
            f"course_id: {request.course_id}\n"
            f"course_name: {request.course_name}\n"
            f"notebook_id: {request.notebook_id or request.course_id}\n"
            f"knowledge_point_id: {request.knowledge_point_id}\n"
            f"knowledge_point_name: {request.knowledge_point_name}\n"
            f"source_document_ids: {request.source_document_ids}\n"
            f"needs_source_context: {needs_source_context}\n"
            f"question: {request.question}\n"
            f"student_profile: {request.student_profile}\n"
            f"code_snippet: {request.code_snippet}\n"
            f"retrieved_context: {rag_context}\n"
            "请生成个性化辅导结果。"
        )
        return system_prompt, user_prompt

    def _require_keys(self, payload: dict[str, Any], keys: list[str]) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise AIServiceError(f"Tutor Agent response missing keys: {missing}")


def _needs_reasoning(request: TutorAskRequest) -> bool:
    if request.code_snippet:
        return True

    question = request.question.lower()
    return len(question) >= 120 or any(
        marker in question for marker in REASONING_QUESTION_MARKERS
    )


def _needs_source_context(request: TutorAskRequest) -> bool:
    question = request.question.lower()
    return any(marker in question for marker in SOURCE_GROUNDED_QUESTION_MARKERS)


def _source_gap_response() -> dict[str, Any]:
    return {
        "answer": (
            "当前 notebook 的所选来源范围内没有检索到足够相关的内容，"
            "无法可靠地基于来源回答这个问题。请先上传并等待来源处理完成，"
            "或在来源栏选择包含该主题的来源后再提问。"
        ),
        "guidance_steps": [
            "确认来源已经处理成功。",
            "检查来源栏中是否选中了相关文档。",
            "换一种更具体的问法，或补充包含该问题内容的来源。",
        ],
        "follow_up_questions": [
            "需要我根据当前已选来源总结可回答的主题吗？",
        ],
        "personalization": {
            "agent": "Tutor Agent",
            "reasoning_basis": ["source_scope"],
            "evidence_gap": "no relevant retrieved context in current source scope",
        },
    }


def _build_citations(rag_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in rag_context:
        document_id = str(item.get("document_id") or item.get("source_id") or "")
        chunk_index = int(item.get("chunk_index") or 0)
        key = (document_id, chunk_index)
        if not document_id or key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "source_id": item.get("source_id") or document_id,
                "document_id": document_id,
                "source_title": item.get("source_title") or document_id,
                "chunk_index": chunk_index,
            }
        )
    return citations
