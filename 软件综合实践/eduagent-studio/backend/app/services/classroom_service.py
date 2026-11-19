import json
import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import ValidationError

from app.db.repositories import ResourceTaskRepository
from app.models.classroom import (
    ClassroomFlashcardSet,
    ClassroomQuizArtifact,
    ClassroomScene,
    ClassroomSession,
    FlashcardPracticeRecord,
    QuizPracticeRecord,
)
from app.models.rag import RAGDocument
from app.schemas.classroom import (
    ClassroomFlashcardsGenerateRequest,
    ClassroomGenerateRequest,
    FlashcardPracticeRecordRequest,
    ClassroomQuizGenerateRequest,
    QuizPracticeRecordRequest,
)
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient
from app.services.rag_retrieval import resolve_rag_documents, retrieve_rag_context


CLASSROOM_RESPONSE_SCHEMA = {
    "title": "string",
    "description": "string",
    "learning_goals": ["string"],
    "agents": [
        {
            "id": "string",
            "name": "string",
            "role": "teacher|classmate|mentor|quiz_master|whiteboard_tutor",
            "persona": "string",
            "capabilities": ["string"],
        }
    ],
    "scenes": [
        {
            "scene_type": (
                "teacher_explain|classmate_question|discussion|slide|quiz|whiteboard|"
                "interactive|code_interactive|pbl|homework|summary"
            ),
            "title": "string",
            "speaker": "string|null",
            "content": {},
            "actions": [{"action_type": "string", "target": "string", "payload": {}}],
            "order": "integer",
        }
    ],
}

QUIZ_RESPONSE_SCHEMA = {
    "title": "string",
    "questions": [
        {
            "question_id": "string",
            "type": "single_choice",
            "stem": "string",
            "options": ["string", "string", "string", "string"],
            "answer": "string",
            "explanation": "string",
            "option_explanations": {"option text": "one sentence explanation"},
        }
    ],
}

FLASHCARD_RESPONSE_SCHEMA = {
    "title": "string",
    "cards": [
        {
            "card_id": "string",
            "front": "string",
            "back": "string",
        }
    ],
}

USER_PROFILE_RESPONSE_SCHEMA = {
    "summary": "string",
    "radar": [
        {
            "key": "conceptual_understanding",
            "label": "概念理解",
            "score": "integer 0-100",
            "reason": "string",
        }
    ],
    "learning_traits": ["string"],
    "strengths": ["string"],
    "risks": ["string"],
    "recommendations": [
        {"title": "string", "detail": "string", "priority": "high|medium|low"}
    ],
    "learning_resources": [
        {
            "title": "string",
            "url": "https://example.com",
            "language": "zh|en",
            "reason": "string",
        }
    ],
}

MAX_STUDIO_ITEM_COUNT = 10
PROFILE_CONVERSATION_WINDOW = 12
PROFILE_QUIZ_PRACTICE_WINDOW = 30
PROFILE_FLASHCARD_PRACTICE_WINDOW = 30
USER_PROFILE_AI_TIMEOUT_SECONDS = 20
PROFILE_RADAR_AXES = [
    ("conceptual_understanding", "概念理解"),
    ("application_transfer", "应用迁移"),
    ("metacognition", "元认知提问"),
    ("study_consistency", "学习节奏"),
    ("memory_recall", "记忆巩固"),
    ("engagement", "投入度"),
]
PROFILE_LEARNING_RESOURCE_CATALOG = [
    {
        "topics": ["data_structure"],
        "title": "中国大学MOOC：数据结构（浙江大学）",
        "url": "https://www.icourse163.org/course/ZJU-93001",
        "language": "zh",
        "reason": "高校公开课课程页，适合系统复习线性表、树、图和排序等核心内容。",
    },
    {
        "topics": ["computer_network"],
        "title": "中国大学MOOC：计算机网络（哈尔滨工业大学）",
        "url": "https://www.icourse163.org/course/HIT-154005",
        "language": "zh",
        "reason": "公开课程页，适合复习网络体系结构、传输层和应用层协议。",
    },
    {
        "topics": ["computer_network"],
        "title": "中国大学MOOC：计算机网络（中国科学技术大学）",
        "url": "https://www.icourse163.org/course/USTC-1003381001",
        "language": "zh",
        "reason": "高校公开课课程页，适合补充协议分层、路由和端到端通信等知识。",
    },
    {
        "topics": ["computer_network"],
        "title": "哔哩哔哩：计算机网络期末 4 小时速成",
        "url": "https://www.bilibili.com/video/BV1H4kwYHEcR/",
        "language": "zh",
        "reason": "期末复习向视频，适合在考前快速串联网络分层、协议和常见题型。",
    },
    {
        "topics": ["computer_network"],
        "title": "哔哩哔哩：TCP/IP 协议入门",
        "url": "https://www.bilibili.com/video/BV1Pt41137w6/",
        "language": "zh",
        "reason": "小专题视频，适合围绕 TCP/IP 协议族补充传输层和网络层理解。",
    },
    {
        "topics": ["computer_network"],
        "title": "哔哩哔哩：7 天快速通过计算机网络期末",
        "url": "https://www.bilibili.com/video/BV1PK4y1X7ze/",
        "language": "zh",
        "reason": "短周期复习视频，适合按考试重点梳理计算机网络核心概念。",
    },
    {
        "topics": ["operating_system"],
        "title": "中国大学MOOC：操作系统（南京大学）",
        "url": "https://www.icourse163.org/course/NJU-1001571004",
        "language": "zh",
        "reason": "高校操作系统课程页，适合补充进程、内存、文件系统和并发主题。",
    },
    {
        "topics": ["data_structure"],
        "title": "哔哩哔哩：王道数据结构",
        "url": "https://www.bilibili.com/video/BV1b7411N798/",
        "language": "zh",
        "reason": "中文视频课程，适合配合题目训练快速复盘数据结构重点。",
    },
    {
        "topics": ["computer_network"],
        "title": "哔哩哔哩：王道计算机网络",
        "url": "https://www.bilibili.com/video/BV19E411D78Q/",
        "language": "zh",
        "reason": "中文视频课程，适合复习协议分层、TCP/IP 和常见网络题型。",
    },
    {
        "topics": ["computer_network"],
        "title": "哔哩哔哩：计算机网络微课堂",
        "url": "https://www.bilibili.com/video/BV1c4411d7jb/",
        "language": "zh",
        "reason": "中文视频课程，适合按章节补充网络层、传输层和应用层协议。",
    },
    {
        "topics": ["operating_system"],
        "title": "哔哩哔哩：王道操作系统",
        "url": "https://www.bilibili.com/video/BV1YE411D7nH/",
        "language": "zh",
        "reason": "中文视频课程，适合巩固进程调度、同步互斥、死锁和内存管理。",
    },
    {
        "topics": ["computer_organization"],
        "title": "中国大学MOOC：计算机组成原理（哈尔滨工业大学）",
        "url": "https://www.icourse163.org/course/hit-309001",
        "language": "zh",
        "reason": "高校公开课课程页，适合复习 CPU、存储系统和指令系统。",
    },
    {
        "topics": ["computer_organization"],
        "title": "哔哩哔哩：哈工大计算机组成原理",
        "url": "https://www.bilibili.com/video/BV1t4411e7LH/",
        "language": "zh",
        "reason": "中文视频课程，适合按章节补充计算机组成原理基础。",
    },
]
PROFILE_DEFAULT_LEARNING_RESOURCES = [
    {
        "title": item["title"],
        "url": item["url"],
        "language": item["language"],
        "reason": item["reason"],
    }
    for item in PROFILE_LEARNING_RESOURCE_CATALOG
]
PROFILE_VERIFIED_LEARNING_RESOURCE_URLS = {
    item["url"].rstrip("/").lower()
    for item in PROFILE_LEARNING_RESOURCE_CATALOG
}
PROFILE_RESOURCE_TOPIC_LABELS = {
    "computer_network": "计算机网络",
    "data_structure": "数据结构",
    "operating_system": "操作系统",
    "computer_organization": "计算机组成原理",
}
PROFILE_RESOURCE_TOPIC_KEYWORDS = {
    "computer_network": (
        "计算机网络",
        "计网",
        "computer network",
        "network layer",
        "transport layer",
        "application layer",
        "tcp",
        "udp",
        "dns",
        "http",
        "https",
        "osi",
        "ip协议",
        "网络层",
        "传输层",
        "应用层",
        "路由",
        "拥塞",
        "协议分层",
    ),
    "data_structure": (
        "数据结构",
        "data structure",
        "算法",
        "链表",
        "栈",
        "队列",
        "二叉树",
        "排序",
        "哈希",
        "bfs",
        "dfs",
    ),
    "operating_system": (
        "操作系统",
        "operating system",
        "进程",
        "线程",
        "死锁",
        "内存管理",
        "文件系统",
        "调度",
    ),
    "computer_organization": (
        "计算机组成",
        "组成原理",
        "computer organization",
        "cpu",
        "指令系统",
        "存储器",
        "流水线",
    ),
}
PROFILE_INTERNAL_METADATA_KEY = "_generation"
logger = logging.getLogger(__name__)


class ClassroomService:
    def __init__(
        self,
        repository: ResourceTaskRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def generate(self, request: ClassroomGenerateRequest) -> dict[str, Any]:
        session_id = str(uuid4())
        topic = request.topic or request.knowledge_point_id
        rag_context = await retrieve_rag_context(
            repository=self._repository,
            ai_client=self._ai_client,
            course_id=request.course_id,
            query=f"{topic} OpenMAIC 浜掑姩璇惧爞",
            user_id=request.user_id,
            notebook_id=request.notebook_id or request.course_id,
            document_ids=request.source_document_ids,
        )
        generated = await self._generate_classroom(topic, request, rag_context)
        scenes = self._build_scenes(session_id, generated["scenes"])
        session = ClassroomSession(
            session_id=session_id,
            user_id=request.user_id,
            course_id=request.course_id,
            knowledge_point_id=request.knowledge_point_id,
            title=generated["title"],
            description=generated["description"],
            learning_goals=generated["learning_goals"],
            agents=generated["agents"],
            status="completed",
            scene_ids=[scene.scene_id for scene in scenes],
            updated_at=datetime.now(UTC),
        )

        await self._repository.save_classroom_session(session)
        await self._repository.save_classroom_scenes(scenes)

        return {
            "session_id": session.session_id,
            "title": session.title,
            "status": session.status,
            "scene_count": len(scenes),
            "scene_types": [scene.scene_type for scene in scenes],
        }

    async def get_classroom(self, session_id: str) -> dict[str, Any] | None:
        session = await self._repository.get_classroom_session(session_id)
        if session is None:
            return None

        scenes = await self._repository.list_classroom_scenes(session_id)
        result = session.model_dump(mode="json")
        result["scenes"] = [scene.model_dump(mode="json") for scene in scenes]
        return result

    async def generate_quiz(
        self,
        request: ClassroomQuizGenerateRequest,
    ) -> dict[str, Any]:
        source_documents = await self._resolve_selected_source_documents(request)
        source_document_ids = [
            document.document_id for document in source_documents
        ]
        question_count = min(
            request.question_count or _plan_quiz_count(source_documents),
            MAX_STUDIO_ITEM_COUNT,
        )
        rag_context = await retrieve_rag_context(
            repository=self._repository,
            ai_client=self._ai_client,
            course_id=request.course_id,
            query=f"{request.knowledge_point_id or ''} quiz {request.difficulty}",
            user_id=request.user_id,
            notebook_id=request.notebook_id or request.course_id,
            document_ids=source_document_ids,
            limit=max(5, min(question_count, 10)),
        )
        generated = await self._generate_quiz(
            request,
            rag_context,
            question_count,
            source_document_ids,
        )
        questions = _normalize_quiz_questions(
            generated.get("questions", []),
            question_count,
        )
        now = datetime.now(UTC)
        quiz = ClassroomQuizArtifact(
            quiz_id=str(uuid4()),
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=request.notebook_id or request.course_id,
            knowledge_point_id=request.knowledge_point_id,
            title=generated["title"],
            questions=questions,
            source_document_ids=source_document_ids,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_classroom_quiz(quiz)
        return quiz.model_dump(mode="json")

    async def generate_flashcards(
        self,
        request: ClassroomFlashcardsGenerateRequest,
    ) -> dict[str, Any]:
        source_documents = await self._resolve_selected_source_documents(request)
        source_document_ids = [
            document.document_id for document in source_documents
        ]
        card_count = min(
            request.card_count or _plan_flashcard_count(source_documents),
            MAX_STUDIO_ITEM_COUNT,
        )
        rag_context = await retrieve_rag_context(
            repository=self._repository,
            ai_client=self._ai_client,
            course_id=request.course_id,
            query=f"{request.knowledge_point_id or ''} flashcards {request.difficulty}",
            user_id=request.user_id,
            notebook_id=request.notebook_id or request.course_id,
            document_ids=source_document_ids,
            limit=max(5, min(card_count, 10)),
        )
        generated = await self._generate_flashcards(
            request,
            rag_context,
            card_count,
            source_document_ids,
        )
        now = datetime.now(UTC)
        flashcard_set = ClassroomFlashcardSet(
            flashcard_set_id=str(uuid4()),
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=request.notebook_id or request.course_id,
            knowledge_point_id=request.knowledge_point_id,
            title=generated["title"],
            cards=generated["cards"][:card_count],
            source_document_ids=source_document_ids,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_classroom_flashcard_set(flashcard_set)
        return flashcard_set.model_dump(mode="json")

    async def list_studio_artifacts(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any]:
        quizzes = await self._repository.list_classroom_quizzes(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        flashcard_sets = await self._repository.list_classroom_flashcard_sets(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        records = await self._repository.list_flashcard_practice_records(
            user_id=user_id,
        )
        flashcard_set_ids = {item.flashcard_set_id for item in flashcard_sets}
        return {
            "quizzes": [quiz.model_dump(mode="json") for quiz in quizzes],
            "flashcard_sets": [
                flashcard_set.model_dump(mode="json")
                for flashcard_set in flashcard_sets
            ],
            "flashcard_records": [
                record.model_dump(mode="json")
                for record in records
                if record.flashcard_set_id in flashcard_set_ids
            ],
        }

    async def generate_user_profile(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        await self._repository.trim_tutor_history(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            keep=PROFILE_CONVERSATION_WINDOW,
        )
        await self._repository.trim_quiz_practice_records(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            keep=PROFILE_QUIZ_PRACTICE_WINDOW,
        )

        flashcard_sets = await self._repository.list_classroom_flashcard_sets(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        flashcard_set_ids = {item.flashcard_set_id for item in flashcard_sets}
        await self._repository.trim_flashcard_practice_records(
            user_id=user_id,
            flashcard_set_ids=flashcard_set_ids,
            keep=PROFILE_FLASHCARD_PRACTICE_WINDOW,
        )

        sessions = await self._repository.list_recent_tutor_sessions(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            limit=PROFILE_CONVERSATION_WINDOW,
        )
        quiz_records = await self._repository.list_recent_quiz_practice_records(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            limit=PROFILE_QUIZ_PRACTICE_WINDOW,
        )
        flashcard_records = await self._repository.list_recent_flashcard_practice_records(
            user_id=user_id,
            flashcard_set_ids=flashcard_set_ids,
            limit=PROFILE_FLASHCARD_PRACTICE_WINDOW,
        )
        conversation_items = []
        message_count = 0
        for session in sessions:
            messages = await self._repository.list_tutor_messages(session.session_id)
            message_count += len(messages)
            conversation_items.append(
                {
                    "session_id": session.session_id,
                    "knowledge_point_id": session.knowledge_point_id,
                    "question": _clip_text(session.question),
                    "messages": [
                        {
                            "role": message.role,
                            "content": _clip_text(message.content),
                        }
                        for message in messages[-4:]
                    ],
                    "updated_at": session.updated_at.isoformat(),
                }
            )

        signals = _build_profile_signals(
            conversation_count=len(sessions),
            message_count=message_count,
            quiz_records=quiz_records,
            flashcard_records=flashcard_records,
        )
        notebook_context = await self._load_notebook_context(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        if (
            signals["conversation_count"] == 0
            and signals["quiz_attempt_count"] == 0
            and signals["flashcard_attempt_count"] == 0
        ):
            result = _locked_profile_result(user_id, course_id, notebook_id, signals)
            await self._repository.save_user_profile(result)
            return result

        context = _compact_profile_context(
            force_refresh=force_refresh,
            conversations=conversation_items,
            quiz_records=quiz_records,
            flashcard_records=flashcard_records,
            signals=signals,
        )
        if notebook_context:
            context["notebook"] = _compact_notebook_context(notebook_context)
        resource_topic = _infer_profile_resource_topic(
            course_id=course_id,
            notebook_id=notebook_id,
            notebook_context=notebook_context,
            context=context,
        )
        if resource_topic:
            context["notebook_topic"] = PROFILE_RESOURCE_TOPIC_LABELS[resource_topic]
        cached_profile = await self._repository.get_user_profile(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )

        profile_task = asyncio.create_task(self._generate_user_profile(context))
        try:
            generated = await asyncio.wait_for(
                asyncio.shield(profile_task),
                timeout=USER_PROFILE_AI_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            profile_task.cancel()
            with suppress(asyncio.CancelledError):
                await profile_task
            return await self._recover_user_profile_generation_failure(
                user_id=user_id,
                course_id=course_id,
                notebook_id=notebook_id,
                signals=signals,
                cached_profile=cached_profile,
                reason="timeout",
                resource_topic=resource_topic,
            )
        except Exception as exc:
            if not profile_task.done():
                profile_task.cancel()
                with suppress(asyncio.CancelledError):
                    await profile_task
            return await self._recover_user_profile_generation_failure(
                user_id=user_id,
                course_id=course_id,
                notebook_id=notebook_id,
                signals=signals,
                cached_profile=cached_profile,
                reason=f"error:{type(exc).__name__}",
                resource_topic=resource_topic,
            )

        result = _profile_result(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            signals=signals,
            generated=generated,
            resource_topic=resource_topic,
        )
        stored_result = _with_profile_generation_metadata(
            result,
            source="ai",
            reason="success",
        )
        await self._repository.save_user_profile(stored_result)
        return _public_profile_result(stored_result, resource_topic=resource_topic)

    async def get_user_profile(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None = None,
    ) -> dict[str, Any]:
        profile = await self._repository.get_user_profile(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        notebook_context = await self._load_notebook_context(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
        )
        resource_topic = _infer_profile_resource_topic(
            course_id=course_id,
            notebook_id=notebook_id,
            notebook_context=notebook_context,
            context=profile,
        )
        if profile is not None:
            return _public_profile_result(profile, resource_topic=resource_topic)
        return _locked_profile_result(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            signals=_empty_profile_signals(),
        )

    async def _recover_user_profile_generation_failure(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None,
        signals: dict[str, Any],
        cached_profile: dict[str, Any] | None,
        reason: str,
        resource_topic: str | None = None,
    ) -> dict[str, Any]:
        if _is_successful_cached_profile(cached_profile):
            logger.warning(
                "User profile AI generation %s; returning cached profile "
                "user_id=%s course_id=%s notebook_id=%s",
                reason,
                user_id,
                course_id,
                notebook_id,
            )
            return _public_profile_result(cached_profile, resource_topic=resource_topic)

        logger.warning(
            "User profile AI generation %s; returning rule fallback profile "
            "user_id=%s course_id=%s notebook_id=%s",
            reason,
            user_id,
            course_id,
            notebook_id,
        )
        result = _profile_result(
            user_id=user_id,
            course_id=course_id,
            notebook_id=notebook_id,
            signals=signals,
            generated=_fallback_generated_profile(signals),
            resource_topic=resource_topic,
        )
        stored_result = _with_profile_generation_metadata(
            result,
            source="fallback",
            reason=reason,
        )
        await self._repository.save_user_profile(stored_result)
        return _public_profile_result(stored_result, resource_topic=resource_topic)

    async def _load_notebook_context(
        self,
        user_id: str,
        course_id: str,
        notebook_id: str | None,
    ) -> dict[str, Any] | None:
        try:
            return await self._repository.get_notebook_context(
                user_id=user_id,
                course_id=course_id,
                notebook_id=notebook_id,
            )
        except Exception:
            logger.warning(
                "Unable to load notebook context for profile resources "
                "user_id=%s course_id=%s notebook_id=%s",
                user_id,
                course_id,
                notebook_id,
                exc_info=True,
            )
            return None

    async def record_quiz_practice(
        self,
        request: QuizPracticeRecordRequest,
    ) -> dict[str, Any]:
        quiz = await self._repository.get_classroom_quiz(request.quiz_id)
        if quiz is None:
            raise ValueError("quiz not found")
        if quiz.user_id != request.user_id or quiz.course_id != request.course_id:
            raise ValueError("cannot record practice for another user's quiz")

        question = next(
            (
                item
                for item in quiz.questions
                if str(item.get("question_id")) == request.question_id
            ),
            None,
        )
        if question is None:
            raise ValueError("quiz question not found")
        correct_answer = str(question.get("answer") or "")
        now = datetime.now(UTC)
        record = QuizPracticeRecord(
            record_id=str(uuid4()),
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=quiz.notebook_id,
            quiz_id=request.quiz_id,
            question_id=request.question_id,
            selected_answer=request.selected_answer,
            correct_answer=correct_answer,
            is_correct=request.selected_answer == correct_answer,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_quiz_practice_record(record)
        await self._repository.trim_quiz_practice_records(
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=quiz.notebook_id,
            keep=PROFILE_QUIZ_PRACTICE_WINDOW,
        )
        return record.model_dump(mode="json")

    async def record_flashcard_practice(
        self,
        request: FlashcardPracticeRecordRequest,
    ) -> dict[str, Any]:
        flashcard_set = await self._repository.get_classroom_flashcard_set(
            request.flashcard_set_id,
        )
        if flashcard_set is None:
            raise ValueError("未找到闪卡。")
        if (
            flashcard_set.user_id != request.user_id
            or flashcard_set.course_id != request.course_id
        ):
            raise ValueError("不能记录其他用户或课程的闪卡练习。")

        card_ids = {
            str(card.get("card_id"))
            for card in flashcard_set.cards
            if card.get("card_id") is not None
        }
        if request.card_id not in card_ids:
            raise ValueError("未找到当前闪卡中的卡片。")
        study_card_ids = set(request.study_card_ids)
        if request.card_id not in study_card_ids or not study_card_ids.issubset(card_ids):
            raise ValueError("本次练习包含无效的闪卡。")

        existing_records = await self._repository.list_flashcard_practice_records(
            user_id=request.user_id,
            flashcard_set_id=request.flashcard_set_id,
        )
        attempt_records = [
            record
            for record in existing_records
            if record.attempt_id == request.attempt_id
        ]
        existing = next(
            (record for record in attempt_records if record.card_id == request.card_id),
            None,
        )
        answered_card_ids = {record.card_id for record in attempt_records}
        answered_card_ids.add(request.card_id)
        now = datetime.now(UTC)
        record = FlashcardPracticeRecord(
            record_id=existing.record_id if existing else str(uuid4()),
            user_id=request.user_id,
            course_id=request.course_id,
            flashcard_set_id=request.flashcard_set_id,
            attempt_id=request.attempt_id,
            study_card_ids=request.study_card_ids,
            card_id=request.card_id,
            result=request.result,
            attempt_completed=study_card_ids.issubset(answered_card_ids),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        await self._repository.save_flashcard_practice_record(record)
        flashcard_sets = await self._repository.list_classroom_flashcard_sets(
            user_id=request.user_id,
            course_id=request.course_id,
            notebook_id=flashcard_set.notebook_id,
        )
        await self._repository.trim_flashcard_practice_records(
            user_id=request.user_id,
            flashcard_set_ids={item.flashcard_set_id for item in flashcard_sets},
            keep=PROFILE_FLASHCARD_PRACTICE_WINDOW,
        )
        return record.model_dump(mode="json")

    async def reset_flashcard_practice(
        self,
        flashcard_set_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        flashcard_set = await self._repository.get_classroom_flashcard_set(
            flashcard_set_id,
        )
        if flashcard_set is None:
            raise ValueError("未找到闪卡。")
        if flashcard_set.user_id != user_id:
            raise ValueError("不能重置其他用户的闪卡练习。")

        await self._repository.clear_flashcard_practice_records(
            user_id=user_id,
            flashcard_set_id=flashcard_set_id,
        )
        return {"cleared": True, "flashcard_set_id": flashcard_set_id}

    async def delete_quiz(self, quiz_id: str, user_id: str) -> dict[str, Any]:
        deleted = await self._repository.delete_classroom_quiz(
            quiz_id=quiz_id,
            user_id=user_id,
        )
        if not deleted:
            raise ValueError("quiz not found")
        return {"quiz_id": quiz_id, "deleted": True}

    async def delete_flashcard_set(
        self,
        flashcard_set_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        deleted = await self._repository.delete_classroom_flashcard_set(
            flashcard_set_id=flashcard_set_id,
            user_id=user_id,
        )
        if not deleted:
            raise ValueError("flashcard set not found")
        return {"flashcard_set_id": flashcard_set_id, "deleted": True}

    async def _generate_classroom(
        self,
        topic: str,
        request: ClassroomGenerateRequest,
        rag_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are EduAgent Studio's Classroom Agent. Follow a two-stage "
            "interactive classroom generation approach: first form a lesson outline, "
            "then generate multiple scenes. The classroom must include teacher "
            "explanation, classmate questions, whiteboard, quiz, interactive or code "
            "practice, PBL or after-class task, and summary. Ground the content in "
            "the provided course materials and knowledge point."
        )
        user_prompt = (
            f"user_id: {request.user_id}\n"
            f"course_id: {request.course_id}\n"
            f"notebook_id: {request.notebook_id or request.course_id}\n"
            f"knowledge_point_id: {request.knowledge_point_id}\n"
            f"topic: {topic}\n"
            f"source_document_ids: {request.source_document_ids}\n"
            f"retrieved_context: {rag_context}\n"
            "Generate a complete interactive classroom in Chinese."
        )
        generated = await self._ai_client.generate_json(
            agent_name="Classroom Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=CLASSROOM_RESPONSE_SCHEMA,
            use_reasoning=True,
        )
        self._require_keys(
            generated,
            ["title", "description", "learning_goals", "agents", "scenes"],
        )
        return generated

    async def _generate_quiz(
        self,
        request: ClassroomQuizGenerateRequest,
        rag_context: list[dict[str, Any]],
        question_count: int,
        source_document_ids: list[str],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are EduAgent Studio's Quiz Agent. Generate single-choice "
            "questions strictly grounded in the provided course materials. "
            "Each question must have exactly four options, one correct answer, "
            "a short answer explanation, and one concise explanation for every option."
        )
        user_prompt = (
            f"user_id: {request.user_id}\n"
            f"course_id: {request.course_id}\n"
            f"notebook_id: {request.notebook_id or request.course_id}\n"
            f"knowledge_point_id: {request.knowledge_point_id}\n"
            f"source_document_ids: {source_document_ids}\n"
            f"question_count: {question_count}\n"
            f"difficulty: {request.difficulty}\n"
            f"retrieved_context: {rag_context}\n"
            "Generate a quiz in Chinese."
        )
        generated = await self._ai_client.generate_json(
            agent_name="Quiz Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=QUIZ_RESPONSE_SCHEMA,
            use_reasoning=True,
        )
        self._require_keys(generated, ["title", "questions"])
        return generated

    async def _generate_flashcards(
        self,
        request: ClassroomFlashcardsGenerateRequest,
        rag_context: list[dict[str, Any]],
        card_count: int,
        source_document_ids: list[str],
    ) -> dict[str, Any]:
        system_prompt = (
            "You are EduAgent Studio's Flashcard Agent. Generate concise "
            "memory cards strictly grounded in the provided course materials. "
            "The front should be a question or term, and the back should be the answer."
        )
        user_prompt = (
            f"user_id: {request.user_id}\n"
            f"course_id: {request.course_id}\n"
            f"notebook_id: {request.notebook_id or request.course_id}\n"
            f"knowledge_point_id: {request.knowledge_point_id}\n"
            f"source_document_ids: {source_document_ids}\n"
            f"card_count: {card_count}\n"
            f"difficulty: {request.difficulty}\n"
            f"retrieved_context: {rag_context}\n"
            "Generate flashcards in Chinese."
        )
        generated = await self._ai_client.generate_json(
            agent_name="Flashcard Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=FLASHCARD_RESPONSE_SCHEMA,
            use_reasoning=False,
        )
        self._require_keys(generated, ["title", "cards"])
        return generated

    async def _generate_user_profile(self, context: dict[str, Any]) -> dict[str, Any]:
        topic_label = str(context.get("notebook_topic") or "当前笔记本主题")
        system_prompt = (
            "You are EduAgent Studio's User Profile Agent. Analyze only the recent "
            "compact learning-signal summary provided by the system. Return a concise Chinese "
            "learning profile with exactly the requested radar axes, practical strengths, "
            "risks, next-step recommendations, and learning resource websites for the "
            "current notebook topic. "
            "For learning_resources, prioritize concrete Chinese MOOC course pages "
            "from icourse163.org and concrete Bilibili video pages, including full "
            "courses, exam-review crash courses, and focused topic videos when useful. "
            "If those are insufficient, use other reputable Chinese MOOC course pages. Recommend "
            "only real course or video pages; do not return homepages, generic search-result "
            "pages, placeholder URLs, opaque URLs, unreachable URLs, or resources about "
            "a different subject."
        )
        user_prompt = (
            "请根据下面的近期学习行为生成用户画像。雷达图必须覆盖这些维度："
            f"{[label for _, label in PROFILE_RADAR_AXES]}。分数范围 0-100。\n"
            f"请额外返回 4-6 个和“{topic_label}”直接相关的 learning_resources，"
            "优先使用中国大学MOOC具体课程页"
            "（https://www.icourse163.org/course/...）和哔哩哔哩具体视频页"
            "（https://www.bilibili.com/video/BV...），可以包含完整课程、期末速成、"
            "考前复习和小专题视频。必须是真实存在的课程/视频页面，"
            "不要返回首页、搜索页、404 页面、占位链接、跨学科课程，或只把笔记本名称带入搜索框的链接。\n"
            f"{json.dumps(context, ensure_ascii=False)}"
        )
        generated = await self._ai_client.generate_json(
            agent_name="User Profile Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=USER_PROFILE_RESPONSE_SCHEMA,
            use_reasoning=False,
        )
        self._require_keys(
            generated,
            [
                "summary",
                "radar",
                "learning_traits",
                "strengths",
                "risks",
                "recommendations",
                "learning_resources",
            ],
        )
        return generated

    def _build_scenes(
        self,
        session_id: str,
        scene_payloads: list[dict[str, Any]],
    ) -> list[ClassroomScene]:
        scenes: list[ClassroomScene] = []
        try:
            for index, payload in enumerate(scene_payloads):
                scenes.append(
                    ClassroomScene.model_validate(
                        {
                            "scene_id": str(uuid4()),
                            "session_id": session_id,
                            "scene_type": payload["scene_type"],
                            "title": payload["title"],
                            "speaker": payload.get("speaker"),
                            "content": payload.get("content", {}),
                            "actions": payload.get("actions", []),
                            "order": payload.get("order", index + 1),
                        }
                    )
                )
        except (KeyError, ValidationError) as exc:
            raise AIServiceError("Classroom Agent returned invalid scenes") from exc

        scenes.sort(key=lambda scene: scene.order)
        return scenes

    def _require_keys(self, payload: dict[str, Any], keys: list[str]) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise AIServiceError(f"Classroom Agent response missing keys: {missing}")

    async def _resolve_selected_source_documents(
        self,
        request: ClassroomQuizGenerateRequest | ClassroomFlashcardsGenerateRequest,
    ) -> list[RAGDocument]:
        if not request.source_document_ids:
            raise ValueError("请至少选择一个资料来源。")

        documents = await resolve_rag_documents(
            repository=self._repository,
            course_id=request.course_id,
            user_id=request.user_id,
            notebook_id=request.notebook_id or request.course_id,
            document_ids=request.source_document_ids,
        )
        if not documents:
            raise ValueError("未找到可用于当前用户的选中资料。")
        return documents


def _clip_text(value: str | None, limit: int = 240) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _compact_notebook_context(notebook_context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _clip_text(str(notebook_context.get(key) or ""), 120)
        for key in ("notebook_id", "course_id", "knowledge_point_id", "title")
        if str(notebook_context.get(key) or "").strip()
    }


def _infer_profile_resource_topic(
    *,
    course_id: str,
    notebook_id: str | None,
    notebook_context: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> str | None:
    weighted_sections: list[tuple[str, int]] = [
        ("\n".join([course_id, notebook_id or ""]), 1)
    ]
    if notebook_context:
        weighted_sections.append(
            (
                json.dumps(
                    _compact_notebook_context(notebook_context),
                    ensure_ascii=False,
                    default=str,
                ),
                4,
            )
        )
    if isinstance(context, dict):
        topic_context = {
            key: value
            for key, value in context.items()
            if key != "learning_resources" and not key.startswith("_")
        }
        weighted_sections.append(
            (json.dumps(topic_context, ensure_ascii=False, default=str), 1)
        )

    scores = []
    for topic, keywords in PROFILE_RESOURCE_TOPIC_KEYWORDS.items():
        score = 0
        for text, weight in weighted_sections:
            lowered_text = text.lower()
            score += weight * sum(
                lowered_text.count(keyword.lower()) for keyword in keywords
            )
        if score > 0:
            scores.append((score, topic))
    if not scores:
        return None
    scores.sort(reverse=True)
    return scores[0][1]


def _compact_profile_context(
    *,
    force_refresh: bool,
    conversations: list[dict[str, Any]],
    quiz_records: list[QuizPracticeRecord],
    flashcard_records: list[FlashcardPracticeRecord],
    signals: dict[str, Any],
) -> dict[str, Any]:
    recent_questions = [
        _clip_text(str(item.get("question") or ""), 120)
        for item in conversations[:8]
        if str(item.get("question") or "").strip()
    ]
    recent_dialogue = []
    for item in conversations[:6]:
        messages = item.get("messages")
        if not isinstance(messages, list):
            messages = []
        assistant_messages = [
            _clip_text(str(message.get("content") or ""), 140)
            for message in messages
            if isinstance(message, dict) and message.get("role") == "assistant"
        ]
        recent_dialogue.append(
            {
                "knowledge_point_id": item.get("knowledge_point_id"),
                "question": _clip_text(str(item.get("question") or ""), 120),
                "last_assistant_summary": assistant_messages[-1]
                if assistant_messages
                else "",
            }
        )

    quiz_mistakes = [
        {
            "question_id": record.question_id,
            "selected_answer": _clip_text(record.selected_answer, 60),
            "correct_answer": _clip_text(record.correct_answer, 60),
        }
        for record in quiz_records
        if not record.is_correct
    ][:10]
    flashcard_misses = [
        {"flashcard_set_id": record.flashcard_set_id, "card_id": record.card_id}
        for record in flashcard_records
        if record.result != "correct"
    ][:10]

    return {
        "force_refresh": force_refresh,
        "signals": signals,
        "recent_questions": recent_questions,
        "recent_dialogue": recent_dialogue,
        "quiz_summary": {
            "attempt_count": signals["quiz_attempt_count"],
            "accuracy": signals["quiz_accuracy"],
            "recent_mistakes": quiz_mistakes,
        },
        "flashcard_summary": {
            "attempt_count": signals["flashcard_attempt_count"],
            "accuracy": signals["flashcard_accuracy"],
            "recent_misses": flashcard_misses,
        },
    }


def _build_profile_signals(
    conversation_count: int,
    message_count: int,
    quiz_records: list[QuizPracticeRecord],
    flashcard_records: list[FlashcardPracticeRecord],
) -> dict[str, Any]:
    quiz_attempt_count = len(quiz_records)
    flashcard_attempt_count = len(flashcard_records)
    quiz_correct = sum(1 for record in quiz_records if record.is_correct)
    flashcard_correct = sum(
        1 for record in flashcard_records if record.result == "correct"
    )
    return {
        "conversation_count": conversation_count,
        "message_count": message_count,
        "quiz_attempt_count": quiz_attempt_count,
        "flashcard_attempt_count": flashcard_attempt_count,
        "quiz_accuracy": round(quiz_correct / quiz_attempt_count, 4)
        if quiz_attempt_count
        else 0.0,
        "flashcard_accuracy": round(flashcard_correct / flashcard_attempt_count, 4)
        if flashcard_attempt_count
        else 0.0,
    }


def _empty_profile_signals() -> dict[str, Any]:
    return {
        "conversation_count": 0,
        "message_count": 0,
        "quiz_attempt_count": 0,
        "flashcard_attempt_count": 0,
        "quiz_accuracy": 0.0,
        "flashcard_accuracy": 0.0,
    }


def _profile_window() -> dict[str, int]:
    return {
        "conversation_limit": PROFILE_CONVERSATION_WINDOW,
        "quiz_practice_limit": PROFILE_QUIZ_PRACTICE_WINDOW,
        "flashcard_practice_limit": PROFILE_FLASHCARD_PRACTICE_WINDOW,
    }


def _with_profile_generation_metadata(
    profile: dict[str, Any],
    source: str,
    reason: str,
) -> dict[str, Any]:
    result = profile.copy()
    result[PROFILE_INTERNAL_METADATA_KEY] = {
        "source": source,
        "reason": reason,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    return result


def _public_profile_result(
    profile: dict[str, Any],
    resource_topic: str | None = None,
) -> dict[str, Any]:
    result = {
        key: value
        for key, value in profile.items()
        if key != PROFILE_INTERNAL_METADATA_KEY
    }
    if result.get("is_unlocked"):
        result["learning_resources"] = _normalize_learning_resources(
            result.get("learning_resources"),
            resource_topic=resource_topic,
        )
    return result


def _is_successful_cached_profile(profile: dict[str, Any] | None) -> bool:
    if not profile or not profile.get("is_unlocked"):
        return False

    metadata = profile.get(PROFILE_INTERNAL_METADATA_KEY)
    if isinstance(metadata, dict) and metadata.get("source") == "fallback":
        return False

    signals = profile.get("signals")
    if isinstance(signals, dict) and profile.get("summary") == _fallback_profile_summary(signals):
        return False
    return True


def _locked_profile_result(
    user_id: str,
    course_id: str,
    notebook_id: str | None,
    signals: dict[str, Any],
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "course_id": course_id,
        "notebook_id": notebook_id,
        "is_unlocked": False,
        "generated_at": datetime.now(UTC).isoformat(),
        "window": _profile_window(),
        "signals": signals,
        "summary": "还没有足够的学习记录生成画像。先在本笔记本中向 AI 提问、完成测验或复习闪卡，画像会自动解锁。",
        "radar": [
            {
                "key": key,
                "label": label,
                "score": 0,
                "reason": "等待更多学习行为。",
            }
            for key, label in PROFILE_RADAR_AXES
        ],
        "learning_traits": [],
        "strengths": [],
        "risks": [],
        "recommendations": [
            {
                "title": "先积累一次学习行为",
                "detail": "在互动课堂、智能辅导或资源中心发起对话，或完成一次测验/闪卡复习后再查看画像。",
                "priority": "medium",
            }
        ],
        "learning_resources": [],
    }


def _profile_result(
    user_id: str,
    course_id: str,
    notebook_id: str | None,
    signals: dict[str, Any],
    generated: dict[str, Any],
    resource_topic: str | None = None,
) -> dict[str, Any]:
    recommendations = _normalize_recommendations(generated.get("recommendations"))
    learning_resources = _normalize_learning_resources(
        generated.get("learning_resources"),
        resource_topic=resource_topic,
    )
    return {
        "user_id": user_id,
        "course_id": course_id,
        "notebook_id": notebook_id,
        "is_unlocked": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "window": _profile_window(),
        "signals": signals,
        "summary": _string_or_default(
            generated.get("summary"),
            _fallback_profile_summary(signals),
        ),
        "radar": _normalize_profile_radar(generated.get("radar"), signals),
        "learning_traits": _string_list(
            generated.get("learning_traits"),
            5,
        ),
        "strengths": _string_list(generated.get("strengths"), 4),
        "risks": _string_list(generated.get("risks"), 4),
        "recommendations": recommendations
        or _fallback_profile_recommendations(signals),
        "learning_resources": learning_resources,
    }


def _normalize_profile_radar(
    payload: Any,
    signals: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        payload = []
    payload_by_key = {
        str(item.get("key")): item for item in payload if isinstance(item, dict)
    }
    payload_by_label = {
        str(item.get("label")): item for item in payload if isinstance(item, dict)
    }
    metrics = []
    for key, label in PROFILE_RADAR_AXES:
        item = payload_by_key.get(key) or payload_by_label.get(label)
        metrics.append(
            {
                "key": key,
                "label": label,
                "score": _coerce_score(
                    item.get("score")
                    if item is not None
                    else _profile_axis_default_score(key, signals),
                ),
                "reason": _string_or_default(
                    item.get("reason") if item is not None else "",
                    _profile_axis_default_reason(key, signals),
                ),
            }
        )
    return metrics


def _normalize_recommendations(
    payload: Any,
) -> list[dict[str, str]]:
    recommendations = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            detail = str(item.get("detail") or "").strip()
            priority = str(item.get("priority") or "medium").lower()
            if priority not in {"high", "medium", "low"}:
                priority = "medium"
            if title and detail:
                recommendations.append(
                    {"title": title, "detail": detail, "priority": priority}
                )
    if recommendations:
        return recommendations[:4]
    return []


def _normalize_learning_resources(
    payload: Any,
    resource_topic: str | None = None,
) -> list[dict[str, str]]:
    resources = []
    seen_urls: set[str] = set()
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            reason = str(item.get("reason") or "").strip()
            language = str(item.get("language") or "zh").lower()
            if language not in {"zh", "en"}:
                language = "zh" if "cn" in language else "en"
            url_key = _resource_url_key(url)
            if (
                title
                and reason
                and _is_preferred_learning_resource_url(
                    url,
                    resource_topic=resource_topic,
                )
                and url_key not in seen_urls
            ):
                resources.append(
                    {
                        "title": title,
                        "url": url,
                        "language": language,
                        "reason": reason,
                    }
                )
                seen_urls.add(url_key)
    merged = _sort_learning_resources(resources)
    for item in _catalog_learning_resources(resource_topic):
        url_key = _resource_url_key(item["url"])
        if url_key in seen_urls:
            continue
        merged.append(item.copy())
        seen_urls.add(url_key)
        if len(merged) >= 6:
            break
    return merged[:6]


def _is_http_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


def _is_preferred_learning_resource_url(
    value: str,
    resource_topic: str | None = None,
) -> bool:
    if not _is_http_url(value):
        return False
    url_key = _resource_url_key(value)
    if url_key not in PROFILE_VERIFIED_LEARNING_RESOURCE_URLS:
        return False
    if resource_topic and url_key not in {
        _resource_url_key(item["url"])
        for item in _catalog_learning_resources(resource_topic)
    }:
        return False

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")

    if host == "icourse163.org":
        return path.startswith("/course/") and len(path) > len("/course/")
    if host == "bilibili.com":
        return path.startswith("/video/BV") and len(path) > len("/video/")
    if host == "xuetangx.com":
        return path.startswith("/course/") and len(path) > len("/course/")
    if host == "higher.smartedu.cn":
        return path.startswith("/course") and len(path) > len("/course")
    return False


def _catalog_learning_resources(
    resource_topic: str | None = None,
) -> list[dict[str, str]]:
    selected = []
    for item in PROFILE_LEARNING_RESOURCE_CATALOG:
        if resource_topic and resource_topic not in item.get("topics", []):
            continue
        selected.append(
            {
                "title": str(item["title"]),
                "url": str(item["url"]),
                "language": str(item["language"]),
                "reason": str(item["reason"]),
            }
        )
    if selected or not resource_topic:
        return selected
    return PROFILE_DEFAULT_LEARNING_RESOURCES.copy()


def _resource_url_key(value: str) -> str:
    return value.rstrip("/").lower()


def _sort_learning_resources(
    resources: list[dict[str, str]],
) -> list[dict[str, str]]:
    priority = {
        "icourse163.org": 0,
        "bilibili.com": 1,
        "xuetangx.com": 2,
        "higher.smartedu.cn": 3,
    }

    def sort_key(item: dict[str, str]) -> tuple[int, int, str]:
        parsed = urlparse(item["url"])
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        language_rank = 0 if item.get("language") == "zh" else 1
        return (priority.get(host, 99), language_rank, item["title"])

    return sorted(resources, key=sort_key)


def _string_list(payload: Any, limit: int) -> list[str]:
    if isinstance(payload, list):
        values = [str(item).strip() for item in payload if str(item).strip()]
        if values:
            return values[:limit]
    return []


def _string_or_default(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _string_required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise AIServiceError(f"User Profile Agent response missing {field_name}")
    return text


def _coerce_score(value: Any) -> int:
    try:
        score = round(float(value))
    except (TypeError, ValueError):
        score = 50
    return max(0, min(100, score))


def _profile_axis_default_score(key: str, signals: dict[str, Any]) -> int:
    quiz_accuracy = float(signals.get("quiz_accuracy") or 0)
    flashcard_accuracy = float(signals.get("flashcard_accuracy") or 0)
    conversation_count = int(signals.get("conversation_count") or 0)
    quiz_count = int(signals.get("quiz_attempt_count") or 0)
    flashcard_count = int(signals.get("flashcard_attempt_count") or 0)
    if key == "conceptual_understanding":
        return 58 + round(quiz_accuracy * 24)
    if key == "application_transfer":
        return 52 + min(18, quiz_count // 2) + round(quiz_accuracy * 12)
    if key == "metacognition":
        return 52 + min(28, conversation_count * 2)
    if key == "study_consistency":
        return 50 + min(20, (conversation_count + quiz_count + flashcard_count) // 2)
    if key == "memory_recall":
        return 52 + min(18, flashcard_count // 2) + round(flashcard_accuracy * 12)
    return 54 + min(30, conversation_count + quiz_count // 3 + flashcard_count // 3)


def _profile_axis_default_reason(key: str, signals: dict[str, Any]) -> str:
    if key == "conceptual_understanding":
        return "根据近期测验正确率和对话记录估算。"
    if key == "application_transfer":
        return "根据练习次数和答题结果估算。"
    if key == "metacognition":
        return "根据近期提问数量和对话活跃度估算。"
    if key == "study_consistency":
        return "根据对话、测验和闪卡练习的综合频次估算。"
    if key == "memory_recall":
        return "根据闪卡复习记录和正确率估算。"
    return "根据近期学习行为总量估算。"


def _fallback_profile_summary(signals: dict[str, Any]) -> str:
    return (
        "近期学习记录已覆盖对话、测验或闪卡练习。系统根据这些行为生成了临时画像；"
        "继续积累错题复盘和闪卡复习后，画像会更稳定。"
    )


def _fallback_profile_recommendations(
    signals: dict[str, Any],
) -> list[dict[str, str]]:
    recommendations = [
        {
            "title": "复盘最近错题",
            "detail": "把答错的题重新解释一遍，再做一道同类型题验证是否真正掌握。",
            "priority": "high",
        },
        {
            "title": "用闪卡巩固关键概念",
            "detail": "每天挑选 5-10 张卡片复习，优先处理上一次答错或犹豫的卡片。",
            "priority": "medium",
        },
    ]
    if int(signals.get("conversation_count") or 0) < 3:
        recommendations.append(
            {
                "title": "增加针对性提问",
                "detail": "围绕一个具体概念追问定义、例子和反例，帮助系统更准确判断理解状态。",
                "priority": "medium",
            }
        )
    return recommendations[:4]


def _fallback_generated_profile(signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": _fallback_profile_summary(signals),
        "radar": [
            {
                "key": key,
                "label": label,
                "score": _profile_axis_default_score(key, signals),
                "reason": _profile_axis_default_reason(key, signals),
            }
            for key, label in PROFILE_RADAR_AXES
        ],
        "learning_traits": ["有近期学习记录", "适合短周期复盘"],
        "strengths": ["已经开始通过对话或练习暴露理解状态。"],
        "risks": ["画像仍依赖近期样本，建议继续积累更多练习记录。"],
        "recommendations": _fallback_profile_recommendations(signals),
        "learning_resources": PROFILE_DEFAULT_LEARNING_RESOURCES,
    }


def _normalize_quiz_questions(
    questions: list[dict[str, Any]],
    question_count: int,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, question in enumerate(questions):
        options = [
            str(option).strip()
            for option in question.get("options", [])
            if str(option).strip()
        ]
        if len(options) < 4:
            continue

        options = options[:4]
        answer = str(question.get("answer") or "").strip()
        if answer not in options:
            answer = options[0]

        explanation = str(question.get("explanation") or "").strip()
        option_explanations = question.get("option_explanations")
        if not isinstance(option_explanations, dict):
            option_explanations = {}

        normalized.append(
            {
                "question_id": str(question.get("question_id") or f"q{index + 1}"),
                "type": "single_choice",
                "stem": str(question.get("stem") or "").strip(),
                "options": options,
                "answer": answer,
                "explanation": explanation,
                "option_explanations": {
                    option: _option_explanation(
                        option,
                        answer,
                        option_explanations,
                        explanation,
                    )
                    for option in options
                },
            }
        )

    if not normalized:
        raise AIServiceError("Quiz Agent returned no valid four-option questions")
    return normalized[:question_count]


def _option_explanation(
    option: str,
    answer: str,
    option_explanations: dict[Any, Any],
    answer_explanation: str,
) -> str:
    explanation = str(option_explanations.get(option) or "").strip()
    if explanation:
        return explanation
    if option == answer and answer_explanation:
        return answer_explanation
    if option == answer:
        return "该选项符合来源材料中的关键信息。"
    return "该选项与来源材料中的关键信息不完全一致。"


def _plan_quiz_count(documents: list[RAGDocument]) -> int:
    chunk_count = _source_chunk_count(documents)
    return min(MAX_STUDIO_ITEM_COUNT, max(3, chunk_count))


def _plan_flashcard_count(documents: list[RAGDocument]) -> int:
    chunk_count = _source_chunk_count(documents)
    return min(MAX_STUDIO_ITEM_COUNT, max(6, chunk_count * 2))


def _source_chunk_count(documents: list[RAGDocument]) -> int:
    return sum(max(1, document.chunk_count) for document in documents)
