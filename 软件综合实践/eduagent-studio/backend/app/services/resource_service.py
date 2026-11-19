import asyncio
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from bson import ObjectId

from app.db.repositories import ResourceTaskRepository
from app.models.course import Course
from app.models.knowledge_point import KnowledgePoint
from app.models.resource import LearningResource, ResourceType
from app.models.task import AgentTask, TaskEvent
from app.schemas.resource import GenerateResourceRequest
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient
from app.services.rag_retrieval import retrieve_rag_context


RESOURCE_TITLES: dict[ResourceType, str] = {
    "lecture": "课程讲义",
    "exercise": "练习题",
    "mindmap": "思维导图",
    "slide": "PPT 大纲",
    "code_lab": "代码实操案例",
}

RESOURCE_AGENTS: dict[ResourceType, str] = {
    "lecture": "Document Agent",
    "exercise": "Exercise Agent",
    "mindmap": "Mindmap Agent",
    "slide": "Slide Agent",
    "code_lab": "Code Lab Agent",
}

RESOURCE_RESPONSE_SCHEMAS: dict[ResourceType, dict[str, Any]] = {
    "lecture": {
        "title": "string",
        "overview": "string",
        "learning_objectives": ["string"],
        "sections": [
            {"heading": "string", "points": ["string"], "teacher_notes": "string"}
        ],
        "self_check": ["string"],
    },
    "exercise": {
        "title": "string",
        "question_bank": [
            {
                "question_id": "string",
                "type": "single_choice|multiple_choice|short_answer|debug|application",
                "difficulty": "easy|medium|hard",
                "stem": "string",
                "options": ["string"],
                "answer": "string",
                "explanation": "string",
            }
        ],
        "grading_rubric": ["string"],
    },
    "mindmap": {
        "title": "string",
        "root": {"id": "string", "label": "string", "children": []},
        "review_path": ["string"],
    },
    "slide": {
        "title": "string",
        "slides": [
            {
                "slide_no": "integer",
                "title": "string",
                "bullets": ["string"],
                "speaker_notes": "string",
            }
        ],
        "estimated_minutes": "integer",
    },
    "code_lab": {
        "title": "string",
        "scenario": "string",
        "environment": {"language": "string", "entry_file": "string"},
        "tasks": ["string"],
        "starter_code": "string",
        "reference_solution": "string",
        "test_cases": [{"name": "string", "input": "string", "expected": "string"}],
    },
}

RESOURCE_RECOMMENDATION_SCHEMA = {
    "items": [
        {
            "id": "string",
            "title": "string",
            "authors": ["string"],
            "source": "string",
            "cover_url": "string",
            "description": "string",
            "level": "入门|进阶|实战",
            "tags": ["string"],
            "related_knowledge_points": ["string"],
            "reason": "string",
            "url": "https://example.com",
        }
    ]
}


class ResourceGenerateService:
    def __init__(
        self,
        repository: ResourceTaskRepository,
        ai_client: AIClient | None = None,
    ):
        self._repository = repository
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def generate(self, request: GenerateResourceRequest) -> dict:
        task_id = str(uuid4())
        task = AgentTask(
            task_id=task_id,
            user_id=request.user_id,
            course_id=request.course_id,
            knowledge_point_id=request.knowledge_point_id,
            status="running",
            progress=0,
            current_stage="context",
            events=[TaskEvent(stage="context", message="学习上下文分析中", progress=20)],
        )
        await self._repository.save_task(task)

        resources: list[LearningResource] = []
        for resource_type in request.resource_types:
            task.events.append(
                TaskEvent(stage="generation", message="资源生成中", progress=75)
            )
            task.current_stage = "generation"
            task.progress = 75
            task.updated_at = datetime.now(UTC)
            await self._repository.save_task(task)

            resources.append(
                await self._build_resource(task_id, request, resource_type)
            )

        task.events.extend(
            [
                TaskEvent(stage="audit", message="安全审核中", progress=90),
                TaskEvent(stage="completed", message="已完成", progress=100),
            ]
        )
        task.status = "completed"
        task.progress = 100
        task.current_stage = "completed"
        task.resource_ids = [resource.resource_id for resource in resources]
        task.updated_at = datetime.now(UTC)

        await self._repository.save_resources(resources)
        await self._repository.save_task(task)

        return {
            "task_id": task.task_id,
            "status": task.status,
            "resource_ids": task.resource_ids,
        }

    async def list_resources(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> dict:
        resources = await self._repository.list_resources(
            user_id=user_id,
            course_id=course_id,
            knowledge_point_id=knowledge_point_id,
            resource_type=resource_type,
        )
        return {
            "items": [
                resource.model_dump(
                    mode="json",
                    exclude={"content", "updated_at"},
                )
                for resource in resources
            ],
            "total": len(resources),
        }

    async def get_resource(self, resource_id: str) -> dict | None:
        resource = await self._repository.get_resource(resource_id)
        if resource is None:
            return None
        return resource.model_dump(mode="json")

    async def delete_resource(self, resource_id: str) -> bool:
        return await self._repository.delete_resource(resource_id)

    async def recommendations(
        self,
        course_id: str,
        course_name: str | None = None,
        knowledge_point_id: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        context = await _resolve_learning_context(course_id, knowledge_point_id, course_name)
        context["query"] = _clean_text(query)
        if query and query.strip() and not context.get("knowledge_point_name"):
            context["knowledge_point_name"] = query.strip()
            context["knowledge_point_description"] = query.strip()
        search_query = _build_recommendation_query(context, query)

        try:
            web_items = await asyncio.wait_for(
                _search_public_resources(search_query, context),
                timeout=5.0,
            )
        except Exception:
            web_items = []

        if web_items:
            return {
                "items": web_items,
                "source": "web",
                **_recommendation_debug_payload(context),
            }

        try:
            agent_items = await asyncio.wait_for(
                _agent_resource_recommendations(
                    search_query,
                    context,
                    self._ai_client,
                ),
                timeout=5.0,
            )
        except Exception:
            agent_items = []

        if agent_items:
            return {
                "items": agent_items,
                "source": "agent",
                **_recommendation_debug_payload(context),
            }

        return {
            "items": _fallback_recommendations(context),
            "source": "fallback",
            **_recommendation_debug_payload(context),
        }

    async def _build_resource(
        self,
        task_id: str,
        request: GenerateResourceRequest,
        resource_type: ResourceType,
    ) -> LearningResource:
        agent_name = RESOURCE_AGENTS[resource_type]
        rag_context = await retrieve_rag_context(
            repository=self._repository,
            ai_client=self._ai_client,
            course_id=request.course_id,
            query=f"{request.knowledge_point_id} {RESOURCE_TITLES[resource_type]}",
        )
        content = await self._generate_resource_content(
            request=request,
            resource_type=resource_type,
            agent_name=agent_name,
            rag_context=rag_context,
        )
        title = content.get("title") or (
            f"{RESOURCE_TITLES[resource_type]} - {request.knowledge_point_id}"
        )
        return LearningResource(
            resource_id=str(uuid4()),
            task_id=task_id,
            user_id=request.user_id,
            course_id=request.course_id,
            knowledge_point_id=request.knowledge_point_id,
            type=resource_type,
            title=title,
            content=content,
        )

    async def _generate_resource_content(
        self,
        request: GenerateResourceRequest,
        resource_type: ResourceType,
        agent_name: str,
        rag_context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system_prompt = (
            f"你是 EduAgent Studio 的 {agent_name}。"
            "你必须基于学生信息、知识点和检索到的课程资料生成真实可用的学习资源。"
            "不要编造引用；如果检索资料不足，在 JSON 中明确指出 evidence_gap。"
        )
        user_prompt = (
            f"user_id: {request.user_id}\n"
            f"course_id: {request.course_id}\n"
            f"knowledge_point_id: {request.knowledge_point_id}\n"
            f"resource_type: {resource_type}\n"
            f"retrieved_context: {rag_context}\n"
            "请生成个性化学习资源。"
        )
        generated = await self._ai_client.generate_json(
            agent_name=agent_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=RESOURCE_RESPONSE_SCHEMAS[resource_type],
            use_reasoning=resource_type in {"exercise", "code_lab"},
        )
        self._require_keys(
            agent_name=agent_name,
            payload=generated,
            keys=RESOURCE_RESPONSE_SCHEMAS[resource_type].keys(),
        )
        generated.update(
            {
                "status": "generated",
                "resource_type": resource_type,
                "agent": agent_name,
                "personalization": {
                    "user_id": request.user_id,
                    "course_id": request.course_id,
                    "knowledge_point_id": request.knowledge_point_id,
                },
                "rag_context": rag_context,
            }
        )
        return generated

    def _require_keys(
        self,
        agent_name: str,
        payload: dict[str, Any],
        keys,
    ) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise AIServiceError(f"{agent_name} response missing keys: {missing}")


async def _resolve_learning_context(
    course_id: str,
    knowledge_point_id: str | None,
    course_name: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "course_id": course_id,
        "course_name": _clean_text(course_name),
        "knowledge_point_id": knowledge_point_id,
        "knowledge_point_name": None,
        "knowledge_point_description": None,
    }

    try:
        course = await Course.get(ObjectId(course_id))
    except Exception:
        course = None
    if course is not None:
        context["course_name"] = course.name
    elif not context["course_name"]:
        context["course_name"] = "当前课程"

    if knowledge_point_id:
        try:
            knowledge_point = await KnowledgePoint.get(ObjectId(knowledge_point_id))
        except Exception:
            knowledge_point = None
        if knowledge_point is not None:
            context["knowledge_point_name"] = knowledge_point.name
            context["knowledge_point_description"] = knowledge_point.description

    return context


def _build_recommendation_query(context: dict[str, Any], query: str | None) -> str:
    parts = [
        _clean_text(context.get("course_name")),
        _clean_text(context.get("knowledge_point_name")),
        _clean_text(query),
    ]
    topic = " ".join(dict.fromkeys(part for part in parts if part))
    return f"{topic or '计算机课程'} 学习资源 open course tutorial textbook documentation"


def _recommendation_debug_payload(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_name": context.get("course_name"),
        "query": context.get("query") or context.get("knowledge_point_name"),
        "knowledge_point_id": context.get("knowledge_point_id"),
        "debug": {
            "knowledge_point_name": context.get("knowledge_point_name"),
            "course_id": context.get("course_id"),
        },
    }


async def _search_public_resources(
    query: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    if os.getenv("TAVILY_API_KEY"):
        return await _search_tavily(query, context)
    if os.getenv("SERPAPI_API_KEY"):
        return await _search_serpapi(query, context)
    if os.getenv("BING_SEARCH_API_KEY"):
        return await _search_bing(query, context)
    return []


async def _agent_resource_recommendations(
    query: str,
    context: dict[str, Any],
    ai_client: AIClient,
) -> list[dict[str, Any]]:
    system_prompt = (
        "你是 EduAgent Studio 的学习资源推荐 Agent。"
        "请只推荐公开、合法、可访问的学习资源，例如开放教材、官方课程、出版社页面、"
        "高校公开课、官方文档或开源教程。不要推荐盗版 PDF、网盘资源或破解下载。"
        "如果不能确认封面图片地址，cover_url 留空。"
    )
    user_prompt = (
        f"course_name: {context.get('course_name')}\n"
        f"knowledge_point_name: {context.get('knowledge_point_name')}\n"
        f"knowledge_point_description: {context.get('knowledge_point_description')}\n"
        f"query: {query}\n"
        "请推荐 6 个适合学生学习的电子书、公开课程或教程资源。"
    )
    system_prompt += (
        " Use course_name, knowledge_point_name, knowledge_point_id, and query as hard constraints. "
        "Recommend only public, legal, accessible resources. "
        "Do not recommend pirated PDFs, cloud-drive dumps, cracked downloads, or mirrors. "
        "Return JSON with an items array."
    )
    user_prompt += (
        f"\nknowledge_point_id: {context.get('knowledge_point_id')}\n"
        f"raw_query: {context.get('query') or query}\n"
        "Return 6 resources specifically useful for this exact knowledge point. "
        "Each item must include id, title, authors, source, cover_url, description, level, "
        "tags, related_knowledge_points, reason, and url."
    )

    payload = await ai_client.generate_json(
        agent_name="Resource Recommendation Agent",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=RESOURCE_RECOMMENDATION_SCHEMA,
        use_reasoning=False,
    )
    return _normalize_agent_recommendations(payload.get("items"), context)


async def _search_tavily(
    query: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": os.getenv("TAVILY_API_KEY"),
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": False,
            },
        )
        response.raise_for_status()
        payload = response.json()

    return _web_results_to_recommendations(payload.get("results", []), context)


async def _search_serpapi(
    query: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(
            "https://serpapi.com/search.json",
            params={
                "api_key": os.getenv("SERPAPI_API_KEY"),
                "engine": "google",
                "q": query,
                "num": 5,
            },
        )
        response.raise_for_status()
        payload = response.json()

    results = [
        {
            "title": item.get("title"),
            "url": item.get("link"),
            "content": item.get("snippet"),
            "source": item.get("source") or "Google Search",
        }
        for item in payload.get("organic_results", [])
    ]
    return _web_results_to_recommendations(results, context)


async def _search_bing(
    query: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(
            "https://api.bing.microsoft.com/v7.0/search",
            params={"q": query, "count": 5, "safeSearch": "Strict"},
            headers={"Ocp-Apim-Subscription-Key": os.getenv("BING_SEARCH_API_KEY", "")},
        )
        response.raise_for_status()
        payload = response.json()

    results = [
        {
            "title": item.get("name"),
            "url": item.get("url"),
            "content": item.get("snippet"),
            "source": item.get("displayUrl") or "Bing Search",
        }
        for item in payload.get("webPages", {}).get("value", [])
    ]
    return _web_results_to_recommendations(results, context)


def _web_results_to_recommendations(
    results: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    recommendations = []
    for index, item in enumerate(results):
        title = _clean_text(item.get("title"))
        url = _clean_text(item.get("url"))
        if not title or not url or not url.startswith(("http://", "https://")):
            continue

        description = _clean_text(item.get("content")) or "公开网络学习资源，建议结合课程目标筛选使用。"
        recommendations.append(
            {
                "id": f"web-{index + 1}",
                "title": title,
                "authors": [],
                "source": _clean_text(item.get("source")) or "web",
                "cover_url": "",
                "description": description,
                "level": _infer_level(title, description),
                "tags": _context_tags(context),
                "related_knowledge_points": _related_points(context),
                "reason": _recommendation_reason(context, "与当前课程或知识点检索结果匹配。"),
                "url": url,
            }
        )
    return recommendations[:5]


def _normalize_agent_recommendations(
    raw_items: Any,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []

    recommendations = []
    for index, raw_item in enumerate(raw_items[:8]):
        if not isinstance(raw_item, dict):
            continue
        title = _clean_text(raw_item.get("title"))
        if not title:
            continue
        recommendations.append(
            {
                "id": _clean_text(raw_item.get("id")) or f"agent-{index + 1}",
                "title": title,
                "authors": _string_list(raw_item.get("authors")),
                "source": _clean_text(raw_item.get("source")) or "AI recommendation",
                "cover_url": _safe_url(raw_item.get("cover_url")),
                "description": _clean_text(raw_item.get("description"))
                or "公开合法学习资源，可结合当前课程目标选择使用。",
                "level": _normalize_level(raw_item.get("level")),
                "tags": _string_list(raw_item.get("tags")) or _context_tags(context),
                "related_knowledge_points": _string_list(
                    raw_item.get("related_knowledge_points")
                )
                or _related_points(context),
                "reason": _clean_text(raw_item.get("reason"))
                or _recommendation_reason(context, "与当前学习上下文匹配。"),
                "url": _safe_url(raw_item.get("url")),
            }
        )
    return recommendations[:6]


def _canonical_course_name(course_name: Any) -> str:
    text = _clean_text(course_name)
    data_structures = "\u6570\u636e\u7ed3\u6784"
    computer_organization = "\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406"
    operating_system = "\u64cd\u4f5c\u7cfb\u7edf"
    computer_network = "\u8ba1\u7b97\u673a\u7f51\u7edc"

    if any(keyword in text for keyword in ("\u7f51\u7edc", "TCP", "IP", "HTTP")):
        return computer_network
    if "\u64cd\u4f5c\u7cfb\u7edf" in text:
        return operating_system
    if any(keyword in text for keyword in ("\u7ec4\u6210", "\u4f53\u7cfb\u7ed3\u6784", "\u8ba1\u7b97\u673a\u7cfb\u7edf")):
        return computer_organization
    if any(keyword in text for keyword in ("\u6570\u636e\u7ed3\u6784", "\u7b97\u6cd5")):
        return data_structures
    return text or "\u5f53\u524d\u8bfe\u7a0b"


def _topic_text(context: dict[str, Any]) -> str:
    return " ".join(
        _clean_text(value)
        for value in (
            context.get("course_name"),
            context.get("knowledge_point_id"),
            context.get("knowledge_point_name"),
            context.get("query"),
        )
        if _clean_text(value)
    ).lower()


def _template_item(
    item_id: str,
    title: str,
    authors: list[str],
    source: str,
    description: str,
    level: str,
    url: str,
) -> tuple[str, str, list[str], str, str, str, str]:
    return (item_id, title, authors, source, description, level, url)


def _topic_fallback_templates(
    course_name: str,
    context: dict[str, Any],
) -> list[tuple[str, str, list[str], str, str, str, str]] | None:
    text = _topic_text(context)
    computer_network = "\u8ba1\u7b97\u673a\u7f51\u7edc"
    operating_system = "\u64cd\u4f5c\u7cfb\u7edf"
    data_structures = "\u6570\u636e\u7ed3\u6784"

    if course_name == computer_network and "tcp" in text:
        return [
            _template_item("fallback-cs144-tcp", "Stanford CS144: Introduction to Computer Networking", ["Stanford University"], "Stanford CS144", "TCP, reliable transport, congestion control, and protocol implementation.", "\u5b9e\u6218", "https://cs144.github.io/"),
            _template_item("fallback-tcp-ip-guide-tcp", "The TCP/IP Guide", ["Charles M. Kozierok"], "tcpipguide.com", "Detailed public reference for TCP/IP protocols and transport behavior.", "\u8fdb\u9636", "http://www.tcpipguide.com/"),
            _template_item("fallback-wireshark-tcp", "Wireshark TCP Lab", ["Kurose & Ross"], "Wireshark Labs", "Packet-trace practice for observing TCP sequence numbers, retransmission, and flow control.", "\u5b9e\u6218", "https://gaia.cs.umass.edu/kurose_ross/wireshark.php"),
            _template_item("fallback-rfc-9293", "RFC 9293: Transmission Control Protocol", ["IETF"], "RFC Editor", "Current public TCP standard from the IETF.", "\u8fdb\u9636", "https://www.rfc-editor.org/rfc/rfc9293"),
            _template_item("fallback-kurose-ross-tcp", "Computer Networking: A Top-Down Approach", ["James F. Kurose", "Keith W. Ross"], "Pearson", "Textbook companion site useful for transport-layer study.", "\u5165\u95e8", "https://gaia.cs.umass.edu/kurose_ross/"),
        ]

    if course_name == computer_network and ("dns" in text or "\u57df\u540d" in text):
        return [
            _template_item("fallback-mdn-dns", "MDN: How DNS works", ["MDN Web Docs"], "MDN", "Readable introduction to domain names and DNS resolution.", "\u5165\u95e8", "https://developer.mozilla.org/en-US/docs/Learn/Common_questions/Web_mechanics/What_is_a_domain_name"),
            _template_item("fallback-cloudflare-dns", "Cloudflare Learning Center: What is DNS?", ["Cloudflare"], "Cloudflare", "Clear resolver, nameserver, record, and caching explanations.", "\u5165\u95e8", "https://www.cloudflare.com/learning/dns/what-is-dns/"),
            _template_item("fallback-wireshark-dns", "Wireshark DNS Lab", ["Kurose & Ross"], "Wireshark Labs", "Hands-on DNS packet capture and analysis.", "\u5b9e\u6218", "https://gaia.cs.umass.edu/kurose_ross/wireshark.php"),
            _template_item("fallback-rfc-1034", "RFC 1034: Domain Names - Concepts and Facilities", ["IETF"], "RFC Editor", "Foundational public DNS architecture specification.", "\u8fdb\u9636", "https://www.rfc-editor.org/rfc/rfc1034"),
            _template_item("fallback-rfc-1035", "RFC 1035: Domain Names - Implementation and Specification", ["IETF"], "RFC Editor", "DNS message, resource record, and implementation details.", "\u8fdb\u9636", "https://www.rfc-editor.org/rfc/rfc1035"),
        ]

    if course_name == operating_system and (
        "virtual" in text or "memory" in text or "\u865a\u62df\u5185\u5b58" in text
    ):
        return [
            _template_item("fallback-ostep-vm", "Operating Systems: Three Easy Pieces", ["Remzi H. Arpaci-Dusseau", "Andrea C. Arpaci-Dusseau"], "OSTEP", "Official open textbook chapters on address spaces, paging, TLBs, and page replacement.", "\u5165\u95e8", "https://pages.cs.wisc.edu/~remzi/OSTEP/"),
            _template_item("fallback-mit-6s081-memory", "MIT 6.S081 Operating System Engineering", ["MIT PDOS"], "MIT PDOS", "xv6 labs and notes for virtual memory implementation.", "\u5b9e\u6218", "https://pdos.csail.mit.edu/6.S081/"),
            _template_item("fallback-xv6-riscv", "xv6-riscv", ["MIT PDOS"], "GitHub", "Teaching operating system source code for studying memory management.", "\u5b9e\u6218", "https://github.com/mit-pdos/xv6-riscv"),
            _template_item("fallback-cs162-vm", "Berkeley CS162 Operating Systems and Systems Programming", ["UC Berkeley"], "Berkeley CS162", "Course material for virtual memory and OS resource management.", "\u8fdb\u9636", "https://cs162.org/"),
            _template_item("fallback-page-replacement", "OpenDSA: Paging", ["OpenDSA Project"], "OpenDSA", "Interactive explanations for paging and replacement ideas.", "\u5165\u95e8", "https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/"),
        ]

    if course_name == operating_system and ("deadlock" in text or "\u6b7b\u9501" in text):
        return [
            _template_item("fallback-ostep-deadlock", "Operating Systems: Three Easy Pieces", ["Remzi H. Arpaci-Dusseau", "Andrea C. Arpaci-Dusseau"], "OSTEP", "Open textbook coverage of deadlock conditions, prevention, avoidance, and detection.", "\u5165\u95e8", "https://pages.cs.wisc.edu/~remzi/OSTEP/"),
            _template_item("fallback-cs162-deadlock", "Berkeley CS162 Operating Systems and Systems Programming", ["UC Berkeley"], "Berkeley CS162", "University OS material connecting synchronization and deadlock.", "\u8fdb\u9636", "https://cs162.org/"),
            _template_item("fallback-geeks-deadlock", "GeeksforGeeks: Deadlock in Operating System", ["GeeksforGeeks"], "GeeksforGeeks", "Quick examples for deadlock conditions and handling strategies.", "\u5165\u95e8", "https://www.geeksforgeeks.org/operating-systems/introduction-of-deadlock-in-operating-system/"),
            _template_item("fallback-bankers", "GeeksforGeeks: Banker's Algorithm", ["GeeksforGeeks"], "GeeksforGeeks", "Practice-oriented explanation of the classic deadlock avoidance algorithm.", "\u5b9e\u6218", "https://www.geeksforgeeks.org/operating-systems/bankers-algorithm-in-operating-system-2/"),
        ]

    if course_name == data_structures and ("tree" in text or "\u6811" in text):
        return [
            _template_item("fallback-opendsa-tree", "OpenDSA: Binary Trees", ["OpenDSA Project"], "OpenDSA", "Interactive chapter for tree and binary tree concepts.", "\u5165\u95e8", "https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/BinaryTree.html"),
            _template_item("fallback-visualgo-bst", "VisuAlgo: Binary Search Tree", ["VisuAlgo Team"], "VisuAlgo", "Interactive BST operations and traversal visualization.", "\u5b9e\u6218", "https://visualgo.net/en/bst"),
            _template_item("fallback-ods-tree", "Open Data Structures", ["Pat Morin"], "opendatastructures.org", "Open textbook chapters on binary trees and search trees.", "\u8fdb\u9636", "https://opendatastructures.org/"),
            _template_item("fallback-mit-6006-tree", "MIT OCW 6.006 Introduction to Algorithms", ["MIT OpenCourseWare"], "MIT OCW", "Lecture material that connects tree structures to algorithm design.", "\u8fdb\u9636", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"),
        ]

    if course_name == data_structures and ("sort" in text or "\u6392\u5e8f" in text):
        return [
            _template_item("fallback-visualgo-sorting", "VisuAlgo: Sorting", ["VisuAlgo Team"], "VisuAlgo", "Interactive sorting algorithm visualization.", "\u5b9e\u6218", "https://visualgo.net/en/sorting"),
            _template_item("fallback-cp-sorting", "CP-Algorithms: Sorting and Searching", ["CP-Algorithms contributors"], "CP-Algorithms", "Implementation-oriented notes for sorting and searching patterns.", "\u5b9e\u6218", "https://cp-algorithms.com/"),
            _template_item("fallback-opendsa-sorting", "OpenDSA: Sorting", ["OpenDSA Project"], "OpenDSA", "Textbook-style sorting concepts and exercises.", "\u5165\u95e8", "https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/Sorting.html"),
            _template_item("fallback-mit-6006-sorting", "MIT OCW 6.006 Introduction to Algorithms", ["MIT OpenCourseWare"], "MIT OCW", "Algorithm analysis and sorting lecture material.", "\u8fdb\u9636", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"),
        ]

    return None


def _course_fallback_templates(
    course_name: str,
) -> list[tuple[str, str, list[str], str, str, str, str]]:
    computer_network = "\u8ba1\u7b97\u673a\u7f51\u7edc"
    operating_system = "\u64cd\u4f5c\u7cfb\u7edf"
    data_structures = "\u6570\u636e\u7ed3\u6784"

    if course_name == computer_network:
        return [
            _template_item("fallback-kurose-ross", "Computer Networking: A Top-Down Approach", ["James F. Kurose", "Keith W. Ross"], "Pearson", "Companion site for a standard networking textbook.", "\u5165\u95e8", "https://gaia.cs.umass.edu/kurose_ross/"),
            _template_item("fallback-stanford-cs144", "Stanford CS144: Introduction to Computer Networking", ["Stanford University"], "Stanford CS144", "Public course with protocol implementation emphasis.", "\u5b9e\u6218", "https://cs144.github.io/"),
            _template_item("fallback-tcp-ip-guide", "The TCP/IP Guide", ["Charles M. Kozierok"], "tcpipguide.com", "Detailed TCP/IP protocol reference.", "\u8fdb\u9636", "http://www.tcpipguide.com/"),
            _template_item("fallback-wireshark-docs", "Wireshark Documentation", ["Wireshark Foundation"], "Wireshark", "Packet analysis documentation and tutorials.", "\u5b9e\u6218", "https://www.wireshark.org/docs/"),
        ]
    if course_name == operating_system:
        return [
            _template_item("fallback-ostep", "Operating Systems: Three Easy Pieces", ["Remzi H. Arpaci-Dusseau", "Andrea C. Arpaci-Dusseau"], "OSTEP", "Official open OS textbook site.", "\u5165\u95e8", "https://pages.cs.wisc.edu/~remzi/OSTEP/"),
            _template_item("fallback-mit-6s081", "MIT 6.S081 Operating System Engineering", ["MIT PDOS"], "MIT PDOS", "xv6-based operating system engineering course.", "\u5b9e\u6218", "https://pdos.csail.mit.edu/6.S081/"),
            _template_item("fallback-cs162", "Berkeley CS162 Operating Systems and Systems Programming", ["UC Berkeley"], "Berkeley CS162", "Public OS course site covering concurrency, memory, and filesystems.", "\u8fdb\u9636", "https://cs162.org/"),
            _template_item("fallback-osdev", "OSDev Wiki", ["OSDev Community"], "OSDev", "Practical OS development reference.", "\u5b9e\u6218", "https://wiki.osdev.org/"),
        ]
    if course_name == data_structures:
        return [
            _template_item("fallback-open-data-structures", "Open Data Structures", ["Pat Morin"], "opendatastructures.org", "Open textbook for core data structures.", "\u5165\u95e8", "https://opendatastructures.org/"),
            _template_item("fallback-mit-6006", "MIT OCW 6.006 Introduction to Algorithms", ["MIT OpenCourseWare"], "MIT OCW", "Open course for algorithms and data structures.", "\u8fdb\u9636", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"),
            _template_item("fallback-visualgo", "VisuAlgo", ["VisuAlgo Team"], "VisuAlgo", "Interactive algorithm and data-structure visualization.", "\u5b9e\u6218", "https://visualgo.net/en"),
            _template_item("fallback-opendsa", "OpenDSA eTextbook", ["OpenDSA Project"], "OpenDSA", "Interactive open textbook and exercises.", "\u8fdb\u9636", "https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/"),
        ]
    return [
        _template_item("fallback-mit-ocw", "MIT OpenCourseWare Computer Science", ["MIT OpenCourseWare"], "MIT OCW", "Public university course collection.", "\u8fdb\u9636", "https://ocw.mit.edu/search/?d=Electrical%20Engineering%20and%20Computer%20Science"),
        _template_item("fallback-khan-cs", "Khan Academy Computing", ["Khan Academy"], "Khan Academy", "Beginner-friendly computing concepts and exercises.", "\u5165\u95e8", "https://www.khanacademy.org/computing"),
        _template_item("fallback-geeksforgeeks", "GeeksforGeeks Computer Science Tutorials", ["GeeksforGeeks"], "GeeksforGeeks", "Concept refreshers and practice examples.", "\u5b9e\u6218", "https://www.geeksforgeeks.org/computer-science-projects/"),
    ]


def _rank_templates_by_topic(
    templates: list[tuple[str, str, list[str], str, str, str, str]],
    context: dict[str, Any],
) -> list[tuple[str, str, list[str], str, str, str, str]]:
    topic_words = {
        word
        for word in _topic_text(context).replace("/", " ").replace("-", " ").split()
        if len(word) >= 2
    }
    if not topic_words:
        return templates

    def score(item: tuple[str, str, list[str], str, str, str, str]) -> int:
        haystack = f"{item[1]} {item[4]} {item[6]}".lower()
        return sum(1 for word in topic_words if word in haystack)

    return sorted(templates, key=score, reverse=True)


def _templates_to_recommendations(
    template_items: list[tuple[str, str, list[str], str, str, str, str]],
    context: dict[str, Any],
    course_name: str,
    knowledge_name: str,
) -> list[dict[str, Any]]:
    tags = _context_tags(context)
    related_points = _related_points(context)
    items = []
    for item_id, title, authors, source, description, level, url in template_items:
        items.append(
            {
                "id": f"{item_id}-{_resource_topic_slug(knowledge_name)}",
                "title": title,
                "authors": authors,
                "source": source,
                "cover_url": "",
                "description": description,
                "level": level,
                "tags": list(dict.fromkeys(tags + [course_name, knowledge_name])),
                "related_knowledge_points": related_points,
                "reason": _recommendation_reason(
                    context,
                    "This resource was selected for the current knowledge point, not only the course.",
                ),
                "url": url,
            }
        )
    return items[:6]


def _fallback_recommendations(context: dict[str, Any]) -> list[dict[str, Any]]:
    course_name = _canonical_course_name(context.get("course_name"))
    knowledge_name = context.get("knowledge_point_name") or course_name
    topic_templates = _topic_fallback_templates(course_name, context)
    if topic_templates is not None:
        return _templates_to_recommendations(
            topic_templates,
            context,
            course_name,
            str(knowledge_name),
        )

    course_templates = _rank_templates_by_topic(
        _course_fallback_templates(course_name),
        context,
    )
    if course_templates:
        return _templates_to_recommendations(
            course_templates,
            context,
            course_name,
            str(knowledge_name),
        )

    tags = _context_tags(context)
    related_points = _related_points(context)
    templates = {
        "数据结构": [
            ("fallback-open-data-structures", "Open Data Structures", ["Pat Morin"], "opendatastructures.org", "开放教材，系统讲解数组、链表、树、图、哈希表等数据结构。", "入门", "https://opendatastructures.org/"),
            ("fallback-mit-6006", "MIT OCW 6.006 Introduction to Algorithms", ["MIT OpenCourseWare"], "MIT OCW", "MIT 公开课，包含算法分析、排序、哈希、树、图算法等主题。", "进阶", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"),
            ("fallback-visualgo", "VisuAlgo", ["VisuAlgo Team"], "visualgo.net", "交互式算法可视化平台，适合观察结构和算法运行过程。", "入门", "https://visualgo.net/en"),
            ("fallback-cp-algorithms", "CP-Algorithms", ["CP-Algorithms contributors"], "cp-algorithms.com", "开源算法资料库，提供实现、复杂度说明和常见技巧。", "实战", "https://cp-algorithms.com/"),
            ("fallback-opendsa", "OpenDSA eTextbook", ["OpenDSA Project"], "Virginia Tech OpenDSA", "开放交互式电子教材，可配合练习和可视化模块学习。", "进阶", "https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/"),
        ],
        "计算机组成原理": [
            ("fallback-cod", "Computer Organization and Design", ["David A. Patterson", "John L. Hennessy"], "Morgan Kaufmann", "经典组成原理教材，覆盖指令系统、处理器和存储层次。", "进阶", "https://www.elsevier.com/books/computer-organization-and-design-risc-v-edition/patterson/978-0-12-820331-6"),
            ("fallback-nand2tetris", "Nand2Tetris", ["Noam Nisan", "Shimon Schocken"], "nand2tetris.org", "通过项目从逻辑门一路搭建到计算机系统。", "入门", "https://www.nand2tetris.org/"),
            ("fallback-csapp", "Computer Systems: A Programmer's Perspective", ["Randal E. Bryant", "David R. O'Hallaron"], "CS:APP", "从程序员视角串联数据表示、存储层次、链接和系统执行。", "进阶", "https://csapp.cs.cmu.edu/"),
            ("fallback-cs61c", "Berkeley CS61C Great Ideas in Computer Architecture", ["UC Berkeley"], "Berkeley CS61C", "围绕机器结构、RISC-V、缓存和并行展开的公开课程。", "实战", "https://cs61c.org/"),
            ("fallback-cmu-15213", "CMU 15-213 Introduction to Computer Systems", ["Carnegie Mellon University"], "CMU 15-213", "系统级课程，适合理解组成原理与程序执行之间的关系。", "进阶", "https://www.cs.cmu.edu/~213/"),
        ],
        "操作系统": [
            ("fallback-ostep", "Operating Systems: Three Easy Pieces", ["Remzi H. Arpaci-Dusseau", "Andrea C. Arpaci-Dusseau"], "OSTEP", "开放教材，系统覆盖虚拟化、并发和持久化。", "入门", "https://pages.cs.wisc.edu/~remzi/OSTEP/"),
            ("fallback-mit-6s081", "MIT 6.S081 Operating System Engineering", ["MIT"], "MIT PDOS", "通过 xv6 实验理解内核、进程、内存和文件系统。", "实战", "https://pdos.csail.mit.edu/6.S081/"),
            ("fallback-xv6-book", "xv6: a simple, Unix-like teaching operating system", ["MIT PDOS"], "xv6 Book", "配合 xv6 源码学习操作系统内核实现。", "进阶", "https://pdos.csail.mit.edu/6.828/2023/xv6/book-riscv-rev3.pdf"),
            ("fallback-cs162", "Berkeley CS162 Operating Systems and Systems Programming", ["UC Berkeley"], "Berkeley CS162", "覆盖并发、内存、文件系统和分布式系统基础的公开课程。", "进阶", "https://cs162.org/"),
            ("fallback-osdev", "OSDev Wiki", ["OSDev Community"], "OSDev", "面向操作系统开发的实践资料和机制说明。", "实战", "https://wiki.osdev.org/"),
        ],
        "计算机网络": [
            ("fallback-kurose-ross", "Computer Networking: A Top-Down Approach", ["James F. Kurose", "Keith W. Ross"], "Pearson", "从应用层向下讲解网络协议和互联网体系。", "入门", "https://gaia.cs.umass.edu/kurose_ross/"),
            ("fallback-stanford-cs144", "Stanford CS144: Introduction to Computer Networking", ["Stanford University"], "Stanford CS144", "以互联网协议栈和 TCP 实现为核心的网络课程。", "实战", "https://cs144.github.io/"),
            ("fallback-cmu-15441", "CMU 15-441 Computer Networks", ["Carnegie Mellon University"], "CMU 15-441", "覆盖网络体系结构、路由、传输和应用协议。", "进阶", "https://www.cs.cmu.edu/~prs/15-441-F10/"),
            ("fallback-tcp-ip-guide", "The TCP/IP Guide", ["Charles M. Kozierok"], "tcpipguide.com", "系统整理 TCP/IP 协议族、寻址、路由和传输机制。", "进阶", "http://www.tcpipguide.com/"),
            ("fallback-mdn-http", "MDN HTTP", ["MDN Web Docs"], "MDN", "HTTP、HTTPS、缓存、状态码和 Web 通信安全的官方式教程。", "入门", "https://developer.mozilla.org/en-US/docs/Web/HTTP"),
            ("fallback-wireshark-docs", "Wireshark Documentation", ["Wireshark Foundation"], "Wireshark", "抓包分析和协议观察工具文档。", "实战", "https://www.wireshark.org/docs/"),
        ],
    }

    generic_templates = [
        ("fallback-openstax", "OpenStax Computer Science", ["OpenStax"], "OpenStax", "\u5f00\u653e\u6559\u6750\u4e0e\u5b66\u4e60\u6750\u6599\u5165\u53e3\uff0c\u53ef\u6309\u5f53\u524d\u8bfe\u7a0b\u4e3b\u9898\u7b5b\u9009\u9605\u8bfb\u3002", "\u5165\u95e8", "https://openstax.org/subjects/computer-science"),
        ("fallback-mit-ocw", "MIT OpenCourseWare Computer Science", ["MIT OpenCourseWare"], "MIT OCW", "\u9ad8\u6821\u516c\u5f00\u8bfe\u7a0b\u96c6\u5408\uff0c\u9002\u5408\u7ed3\u5408\u5f53\u524d\u8bfe\u7a0b\u76ee\u6807\u67e5\u627e\u8bb2\u4e49\u548c\u4f5c\u4e1a\u3002", "\u8fdb\u9636", "https://ocw.mit.edu/search/?d=Electrical%20Engineering%20and%20Computer%20Science"),
        ("fallback-geeksforgeeks", "GeeksforGeeks Computer Science Tutorials", ["GeeksforGeeks"], "GeeksforGeeks", "\u9762\u5411\u6982\u5ff5\u590d\u4e60\u548c\u4f8b\u9898\u7684\u516c\u5f00\u6559\u7a0b\uff0c\u53ef\u4f5c\u4e3a\u8bfe\u540e\u68c0\u7d22\u8865\u5145\u3002", "\u5b9e\u6218", "https://www.geeksforgeeks.org/computer-science-projects/"),
        ("fallback-khan-cs", "Khan Academy Computing", ["Khan Academy"], "Khan Academy", "\u8f7b\u91cf\u5316\u7684\u8ba1\u7b97\u673a\u6982\u5ff5\u548c\u7ec3\u4e60\u8d44\u6e90\uff0c\u9002\u5408\u5165\u95e8\u590d\u4e60\u3002", "\u5165\u95e8", "https://www.khanacademy.org/computing"),
    ]
    template_items = templates.get(course_name, generic_templates)

    items = [
        {
            "id": item_id,
            "title": title,
            "authors": authors,
            "source": source,
            "cover_url": "",
            "description": description,
            "level": level,
            "tags": tags + [course_name],
            "related_knowledge_points": related_points,
            "reason": _recommendation_reason(context, "这是当前课程方向的稳定兜底资源，可用于继续学习和查阅。"),
            "url": url,
        }
        for item_id, title, authors, source, description, level, url in template_items
    ]

    for item in items:
        item["id"] = f"{item['id']}-{_resource_topic_slug(knowledge_name)}"
    return items


def _resource_topic_slug(topic: Any) -> str:
    topic_text = _clean_text(topic)
    slug = "".join(char for char in topic_text.lower() if char.isalnum())
    return slug[:32] or "course"


def _context_tags(context: dict[str, Any]) -> list[str]:
    tags = []
    course_name = context.get("course_name")
    knowledge_name = context.get("knowledge_point_name")
    if course_name:
        tags.append(str(course_name))
    if knowledge_name:
        tags.append(str(knowledge_name))
    return tags or ["\u5f53\u524d\u8bfe\u7a0b"]


def _related_points(context: dict[str, Any]) -> list[str]:
    knowledge_name = context.get("knowledge_point_name")
    if knowledge_name:
        return [str(knowledge_name)]
    course_name = context.get("course_name")
    return [str(course_name)] if course_name else ["\u5f53\u524d\u8bfe\u7a0b"]


def _recommendation_reason(context: dict[str, Any], suffix: str) -> str:
    knowledge_name = context.get("knowledge_point_name")
    if knowledge_name:
        return f"围绕「{knowledge_name}」推荐：{suffix}"
    return f"围绕「{context.get('course_name', '当前课程')}」推荐：{suffix}"


def _infer_level(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if any(keyword in text for keyword in ["advanced", "implementation", "contest", "competitive"]):
        return "实战"
    if any(keyword in text for keyword in ["algorithm", "course", "lecture", "ocw"]):
        return "进阶"
    return "入门"


def _normalize_level(value: Any) -> str:
    cleaned = _clean_text(value)
    if cleaned in {"入门", "进阶", "实战"}:
        return cleaned
    lowered = cleaned.lower()
    if lowered in {"beginner", "basic", "intro"}:
        return "入门"
    if lowered in {"advanced", "practice", "project"}:
        return "实战"
    return "进阶"


def _safe_url(value: Any) -> str:
    cleaned = _clean_text(value)
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    return ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(item) for item in value if _clean_text(item)]


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""
