from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.db.mongodb import get_mongo_database
from app.models.course import Course
from app.models.knowledge_graph import KnowledgeGraphState
from app.models.knowledge_point import KnowledgePoint
from app.schemas.course import (
    CourseCreateRequest,
    KnowledgeGraphUpdateRequest,
    KnowledgePointCreateRequest,
)
from app.services.ai_client import AIClient, AIServiceError, OpenAICompatibleAIClient


KNOWLEDGE_GRAPH_SCHEMA = {
    "course_id": "string",
    "course_name": "string",
    "nodes": [
        {
            "id": "string",
            "label": "string",
            "description": "string",
            "importance": "core|important|normal",
            "mastery": "unknown|weak|medium|mastered",
        }
    ],
    "edges": [
        {
            "source": "string",
            "target": "string",
            "relation": "prerequisite|related|advanced",
            "description": "string",
        }
    ],
    "source": "agent",
    "updated_reason": "string",
}

KNOWLEDGE_GRAPH_EXPANSION_SCHEMA = {
    "nodes": [
        {
            "id": "string",
            "label": "string",
            "description": "string",
            "importance": "core|important|normal",
            "mastery": "unknown",
        }
    ],
    "edges": [
        {
            "source": "string",
            "target": "string",
            "relation": "prerequisite|related|advanced",
            "description": "string",
        }
    ],
    "updated_reason": "string",
}

CHINESE_NODE_LABEL_REPLACEMENTS = {
    "CPU": "中央处理器",
    "CACHE": "高速缓存",
    "TCP": "传输控制协议",
    "UDP": "用户数据报协议",
    "DNS": "域名系统",
    "HTTP": "超文本传输协议",
    "HTTPS": "安全超文本传输协议",
    "HTTP/HTTPS": "网页传输协议",
    "IP": "网际协议",
    "IP协议": "网际协议",
    "I/O管理": "输入输出管理",
    "IO管理": "输入输出管理",
    "I/O系统": "输入输出系统",
    "IO系统": "输入输出系统",
    "OSI/TCP-IP模型": "网络分层模型",
    "OSITCPIP模型": "网络分层模型",
}

FALLBACK_GRAPHS: dict[str, dict[str, Any]] = {
    "数据结构": {
        "nodes": [
            {"id": "complexity", "label": "算法复杂度分析", "description": "用时间复杂度和空间复杂度衡量算法效率，是选择数据结构与算法方案的基础。", "importance": "core"},
            {"id": "linear-list", "label": "线性表", "description": "理解顺序表与链表的存储方式，以及插入、删除、查找操作的代价。", "importance": "core"},
            {"id": "stack-queue", "label": "栈与队列", "description": "掌握 LIFO 与 FIFO 抽象模型，理解递归、表达式求值和层次遍历中的应用。", "importance": "important"},
            {"id": "string-array", "label": "串与数组", "description": "理解数组连续存储、字符串匹配和多维数组地址计算。", "importance": "normal"},
            {"id": "tree", "label": "树与二叉树", "description": "掌握树的递归结构、二叉树性质和常见遍历方式。", "importance": "core"},
            {"id": "graph", "label": "图结构", "description": "理解邻接矩阵、邻接表、DFS、BFS 和连通性分析。", "importance": "core"},
            {"id": "search", "label": "查找", "description": "掌握顺序查找、二分查找、树表查找和散列表查找的适用条件。", "importance": "important"},
            {"id": "sorting", "label": "排序", "description": "比较插入、交换、选择、归并等排序算法的思想与复杂度。", "importance": "important"},
            {"id": "hash-table", "label": "哈希表", "description": "理解哈希函数、冲突处理和平均复杂度分析。", "importance": "normal"},
            {"id": "heap-priority-queue", "label": "堆与优先队列", "description": "掌握堆的结构性质、上滤下滤和优先队列应用。", "importance": "normal"},
            {"id": "union-find", "label": "并查集", "description": "理解集合合并、路径压缩和按秩合并，常用于连通性问题。", "importance": "normal"},
        ],
        "edges": [
            {"source": "complexity", "target": "linear-list", "relation": "prerequisite", "description": "复杂度分析帮助比较线性结构操作代价。"},
            {"source": "linear-list", "target": "stack-queue", "relation": "prerequisite", "description": "栈与队列可以基于顺序表或链表实现。"},
            {"source": "linear-list", "target": "string-array", "relation": "related", "description": "数组是线性结构和字符串存储的重要基础。"},
            {"source": "stack-queue", "target": "tree", "relation": "prerequisite", "description": "树的遍历常借助栈或队列理解。"},
            {"source": "tree", "target": "heap-priority-queue", "relation": "advanced", "description": "堆是具有特殊顺序性质的完全二叉树。"},
            {"source": "tree", "target": "search", "relation": "related", "description": "二叉搜索树是查找结构的重要形式。"},
            {"source": "complexity", "target": "sorting", "relation": "related", "description": "排序算法比较离不开复杂度分析。"},
            {"source": "search", "target": "hash-table", "relation": "advanced", "description": "哈希表提供平均常数时间查找。"},
            {"source": "tree", "target": "graph", "relation": "related", "description": "树可以视作特殊的无环连通图。"},
            {"source": "graph", "target": "union-find", "relation": "advanced", "description": "并查集常用于图的连通性和最小生成树问题。"},
        ],
    },
    "计算机组成原理": {
        "nodes": [
            {"id": "data-representation", "label": "数据表示", "description": "理解二进制、补码、浮点数和字符编码，是分析硬件执行数据的入口。", "importance": "core"},
            {"id": "alu", "label": "运算器", "description": "掌握算术逻辑单元、加法器和状态标志，理解指令执行中的运算过程。", "importance": "important"},
            {"id": "memory-system", "label": "存储系统", "description": "理解寄存器、Cache、主存与外存的层次结构。", "importance": "core"},
            {"id": "instruction-system", "label": "指令系统", "description": "掌握指令格式、寻址方式和机器级程序的基本执行模型。", "importance": "important"},
            {"id": "cpu", "label": "CPU", "description": "理解数据通路、控制信号和指令周期如何协同完成执行。", "importance": "core"},
            {"id": "controller", "label": "控制器", "description": "理解硬布线控制和微程序控制如何产生控制信号。", "importance": "important"},
            {"id": "bus", "label": "总线", "description": "掌握总线结构、仲裁和数据传输时序。", "importance": "normal"},
            {"id": "io-system", "label": "输入输出系统", "description": "理解接口、中断、DMA 和外设通信方式。", "importance": "normal"},
            {"id": "pipeline", "label": "流水线", "description": "理解指令流水线、相关冲突和性能提升机制。", "importance": "important"},
            {"id": "cache", "label": "Cache", "description": "掌握局部性、映射方式、替换策略和一致性问题。", "importance": "core"},
            {"id": "interrupt", "label": "中断机制", "description": "理解异常和中断如何改变处理器控制流。", "importance": "normal"},
        ],
        "edges": [
            {"source": "data-representation", "target": "alu", "relation": "prerequisite", "description": "运算器处理的数据首先依赖机器数表示。"},
            {"source": "alu", "target": "cpu", "relation": "prerequisite", "description": "运算器是 CPU 数据通路的核心部件。"},
            {"source": "instruction-system", "target": "cpu", "relation": "prerequisite", "description": "CPU 的控制流程围绕指令系统展开。"},
            {"source": "controller", "target": "cpu", "relation": "related", "description": "控制器负责驱动 CPU 内部数据流。"},
            {"source": "cpu", "target": "pipeline", "relation": "advanced", "description": "流水线是在 CPU 执行路径上的性能优化。"},
            {"source": "memory-system", "target": "cache", "relation": "advanced", "description": "Cache 是存储层次中最关键的高速缓冲层。"},
            {"source": "bus", "target": "memory-system", "relation": "related", "description": "总线连接 CPU、内存与外设。"},
            {"source": "bus", "target": "io-system", "relation": "related", "description": "I/O 设备通过总线和接口与主机交换数据。"},
            {"source": "interrupt", "target": "io-system", "relation": "related", "description": "中断是 I/O 完成通知和异常处理的重要机制。"},
            {"source": "instruction-system", "target": "pipeline", "relation": "related", "description": "指令格式和执行阶段影响流水线设计。"},
        ],
    },
    "操作系统": {
        "nodes": [
            {"id": "process-thread", "label": "进程与线程", "description": "理解进程、线程、上下文切换和资源隔离，是学习 OS 并发模型的基础。", "importance": "core"},
            {"id": "cpu-scheduling", "label": "处理机调度", "description": "掌握先来先服务、时间片轮转、优先级等调度策略及其指标。", "importance": "important"},
            {"id": "sync-mutual-exclusion", "label": "同步与互斥", "description": "理解临界区、锁、信号量、管程和并发正确性问题。", "importance": "core"},
            {"id": "deadlock", "label": "死锁", "description": "掌握死锁产生条件、预防、避免和检测恢复策略。", "importance": "important"},
            {"id": "memory-management", "label": "内存管理", "description": "理解分页、分段、地址转换和内存分配。", "importance": "core"},
            {"id": "virtual-memory", "label": "虚拟内存", "description": "掌握页表、缺页中断、工作集和地址空间抽象。", "importance": "core"},
            {"id": "file-system", "label": "文件系统", "description": "理解文件目录、索引分配、磁盘布局和持久化组织。", "importance": "important"},
            {"id": "io-management", "label": "I/O 管理", "description": "理解缓冲、缓存、设备驱动和 I/O 调度。", "importance": "normal"},
            {"id": "device-management", "label": "设备管理", "description": "掌握设备抽象、驱动接口和设备分配。", "importance": "normal"},
            {"id": "system-call", "label": "系统调用", "description": "理解用户态与内核态切换，以及系统服务入口。", "importance": "important"},
            {"id": "page-replacement", "label": "页面置换算法", "description": "比较 FIFO、LRU、Clock 等页面置换策略。", "importance": "normal"},
        ],
        "edges": [
            {"source": "process-thread", "target": "cpu-scheduling", "relation": "prerequisite", "description": "调度算法以进程和线程作为调度对象。"},
            {"source": "process-thread", "target": "sync-mutual-exclusion", "relation": "prerequisite", "description": "并发线程共享资源时需要同步与互斥。"},
            {"source": "sync-mutual-exclusion", "target": "deadlock", "relation": "advanced", "description": "不当的资源等待会引发死锁。"},
            {"source": "memory-management", "target": "virtual-memory", "relation": "advanced", "description": "虚拟内存建立在地址转换和分页机制之上。"},
            {"source": "virtual-memory", "target": "page-replacement", "relation": "advanced", "description": "页面置换算法处理缺页后的内存淘汰选择。"},
            {"source": "file-system", "target": "io-management", "relation": "related", "description": "文件系统依赖底层 I/O 管理完成持久化访问。"},
            {"source": "io-management", "target": "device-management", "relation": "related", "description": "设备管理为 I/O 操作提供驱动和抽象。"},
            {"source": "system-call", "target": "file-system", "relation": "related", "description": "文件读写通常通过系统调用进入内核。"},
            {"source": "system-call", "target": "process-thread", "relation": "related", "description": "进程创建、等待和通信都依赖系统调用接口。"},
            {"source": "memory-management", "target": "system-call", "relation": "related", "description": "系统调用过程中涉及用户态和内核态地址空间切换。"},
        ],
    },
    "计算机网络": {
        "nodes": [
            {"id": "tcp-ip-model", "label": "OSI/TCP-IP 模型", "description": "理解分层思想、协议栈职责和数据封装，是学习网络协议的总览框架。", "importance": "core"},
            {"id": "physical-layer", "label": "物理层", "description": "理解信号、介质、编码和比特传输的基本问题。", "importance": "normal"},
            {"id": "data-link-layer", "label": "数据链路层", "description": "掌握成帧、差错检测、MAC 地址和局域网访问控制。", "importance": "important"},
            {"id": "network-layer", "label": "网络层", "description": "理解分组转发、寻址和跨网络通信。", "importance": "core"},
            {"id": "ip-protocol", "label": "IP 协议", "description": "掌握 IP 地址、子网划分、分片和转发规则。", "importance": "core"},
            {"id": "routing-algorithm", "label": "路由算法", "description": "理解距离向量、链路状态和路径选择策略。", "importance": "important"},
            {"id": "transport-layer", "label": "传输层", "description": "掌握端到端通信、端口、可靠传输和复用分用。", "importance": "core"},
            {"id": "tcp", "label": "TCP", "description": "理解连接建立、可靠传输、流量控制和拥塞控制。", "importance": "core"},
            {"id": "udp", "label": "UDP", "description": "掌握无连接传输、低开销和实时应用场景。", "importance": "normal"},
            {"id": "congestion-control", "label": "拥塞控制", "description": "理解慢启动、拥塞避免、快速重传和网络性能调节。", "importance": "important"},
            {"id": "application-layer", "label": "应用层", "description": "理解 HTTP、DNS 等应用协议如何使用传输层服务。", "importance": "important"},
            {"id": "dns", "label": "DNS", "description": "掌握域名解析、递归查询、缓存和资源记录。", "importance": "normal"},
            {"id": "http-https", "label": "HTTP/HTTPS", "description": "理解请求响应、状态码、缓存、TLS 和 Web 通信安全。", "importance": "important"},
        ],
        "edges": [
            {"source": "tcp-ip-model", "target": "physical-layer", "relation": "prerequisite", "description": "分层模型从物理传输开始组织网络知识。"},
            {"source": "physical-layer", "target": "data-link-layer", "relation": "prerequisite", "description": "链路层在物理层比特传输之上组织帧。"},
            {"source": "data-link-layer", "target": "network-layer", "relation": "prerequisite", "description": "网络层依赖链路层完成相邻节点传输。"},
            {"source": "network-layer", "target": "ip-protocol", "relation": "related", "description": "IP 是网络层的核心协议。"},
            {"source": "network-layer", "target": "routing-algorithm", "relation": "advanced", "description": "路由算法决定分组转发路径。"},
            {"source": "network-layer", "target": "transport-layer", "relation": "prerequisite", "description": "传输层在网络层端到端交付基础上提供进程通信。"},
            {"source": "transport-layer", "target": "tcp", "relation": "advanced", "description": "TCP 是传输层可靠连接服务的代表。"},
            {"source": "transport-layer", "target": "udp", "relation": "related", "description": "UDP 提供传输层无连接服务。"},
            {"source": "tcp", "target": "congestion-control", "relation": "advanced", "description": "拥塞控制是 TCP 性能和稳定性的关键机制。"},
            {"source": "transport-layer", "target": "application-layer", "relation": "prerequisite", "description": "应用层协议运行在传输层服务之上。"},
            {"source": "application-layer", "target": "dns", "relation": "related", "description": "DNS 是应用层基础设施协议。"},
            {"source": "application-layer", "target": "http-https", "relation": "related", "description": "HTTP/HTTPS 是 Web 应用通信的核心协议。"},
        ],
    },
}


class CourseService:
    def __init__(self, ai_client: AIClient | None = None):
        self._ai_client = ai_client or OpenAICompatibleAIClient()

    async def create_course(self, data: CourseCreateRequest) -> Course:
        course = Course(
            name=data.name,
            description=data.description,
            teacher_id=ObjectId(data.teacher_id) if data.teacher_id else None,
        )
        await course.insert()
        return course

    async def list_courses(self) -> list[dict]:
        courses = await Course.find_all().to_list()
        return [self._course_to_dict(c) for c in courses]

    async def create_knowledge_point(self, data: KnowledgePointCreateRequest) -> KnowledgePoint:
        kp = KnowledgePoint(
            course_id=ObjectId(data.course_id),
            chapter=data.chapter,
            name=data.name,
            description=data.description,
            difficulty=data.difficulty,
            prerequisites=[ObjectId(pid) for pid in data.prerequisites],
            order=data.order,
        )
        await kp.insert()
        return kp

    async def list_knowledge_points(self, course_id: str) -> list[dict]:
        kps = await KnowledgePoint.find(
            KnowledgePoint.course_id == ObjectId(course_id)
        ).sort("+order").to_list()
        return [self._kp_to_dict(kp) for kp in kps]

    async def get_knowledge_point_graph(self, course_id: str) -> list[dict] | dict[str, Any]:
        stored_graph = await KnowledgeGraphState.find_one(
            KnowledgeGraphState.graph_id == course_id
        )
        if stored_graph is not None:
            return {
                "course_id": stored_graph.graph_id,
                "course_name": stored_graph.course_name,
                "nodes": stored_graph.nodes,
                "edges": stored_graph.edges,
                "source": "database",
                "updated_reason": stored_graph.updated_reason,
            }

        try:
            object_id = ObjectId(course_id)
        except Exception:
            return []

        kps = await KnowledgePoint.find(
            KnowledgePoint.course_id == object_id
        ).sort("+order").to_list()

        kp_map = {str(kp.id): kp for kp in kps}
        result = []
        for kp in kps:
            result.append({
                "id": str(kp.id),
                "name": kp.name,
                "chapter": kp.chapter,
                "description": kp.description,
                "difficulty": kp.difficulty,
                "prerequisites": [
                    {"id": str(pid), "name": kp_map[str(pid)].name}
                    for pid in kp.prerequisites if str(pid) in kp_map
                ],
                "order": kp.order,
            })
        return result

    async def save_knowledge_graph(
        self,
        graph_id: str,
        graph: dict[str, Any],
        course_name: str | None = None,
    ) -> dict[str, Any]:
        stored_payload = _graph_for_storage(graph_id, course_name, graph)
        state = await KnowledgeGraphState.find_one(
            KnowledgeGraphState.graph_id == graph_id
        )
        if state is None:
            state = KnowledgeGraphState(
                graph_id=graph_id,
                course_name=stored_payload["course_name"],
                nodes=stored_payload["nodes"],
                edges=stored_payload["edges"],
                initial_nodes=stored_payload["nodes"],
                initial_edges=stored_payload["edges"],
                source=stored_payload["source"],
                updated_reason=stored_payload["updated_reason"],
            )
            await state.insert()
        else:
            if not state.initial_nodes:
                state.initial_nodes = deepcopy(state.nodes or stored_payload["nodes"])
                state.initial_edges = deepcopy(state.edges or stored_payload["edges"])
            state.course_name = stored_payload["course_name"]
            state.nodes = stored_payload["nodes"]
            state.edges = stored_payload["edges"]
            state.source = stored_payload["source"]
            state.updated_reason = stored_payload["updated_reason"]
            state.updated_at = datetime.now(UTC)
            await state.save()
        return stored_payload

    async def generate_knowledge_graph(self, course_id: str) -> dict[str, Any]:
        stored_graph = await KnowledgeGraphState.find_one(
            KnowledgeGraphState.graph_id == course_id
        )
        if stored_graph is not None and (stored_graph.initial_nodes or stored_graph.nodes):
            return await self._restore_initial_knowledge_graph(stored_graph)

        notebook_title = await self._resolve_notebook_title(course_id)
        if notebook_title:
            try:
                generated = await self._ai_client.generate_json(
                    agent_name="Notebook Knowledge Graph Agent",
                    system_prompt=(
                        "You are EduAgent Studio's knowledge graph agent. "
                        "Generate an initial knowledge graph from the notebook title. "
                        "Use 6 to 10 nodes when possible. Node importance must be core, important, or normal. "
                        "Node labels must use Chinese characters only; do not use English letters, acronyms, digits, or symbols."
                    ),
                    user_prompt=(
                        f"notebook_id: {course_id}\n"
                        f"notebook_title: {notebook_title}\n"
                        "Generate the initial graph. Edges should express prerequisite, related, or advanced relations."
                    ),
                    response_schema=KNOWLEDGE_GRAPH_SCHEMA,
                    use_reasoning=False,
                )
                graph = _normalize_agent_graph(generated, course_id, notebook_title)
            except Exception:
                graph = _fallback_graph_for_course(
                    course_id,
                    notebook_title,
                    "Initial fallback graph generated for notebook.",
                )
            return await self.save_knowledge_graph(course_id, graph, course_name=notebook_title)

        try:
            object_id = ObjectId(course_id)
        except Exception as exc:
            raise ValueError("course not found") from exc

        course = await Course.get(object_id)
        if course is None:
            raise ValueError("course not found")

        existing_points = await self.list_knowledge_points(course_id)
        system_prompt = (
            "你是 EduAgent Studio 的课程知识图谱 Agent。"
            "请根据课程名称、课程描述和已有知识点，生成适合学习平台展示的课程知识图谱。"
            "节点数量控制在 8 到 12 个，边表示先修或关联关系。"
            "所有节点名称和描述必须使用中文；专业缩写可以保留，但节点名称必须同时包含中文。"
            "节点名称只能使用中文汉字，不允许英文、缩写、数字或符号。"
            "节点名称不得重复，也不得生成含义相同的重复节点。"
            "只推荐课程内部知识点，不要编造外部下载资源。"
        )
        user_prompt = (
            f"course_id: {course_id}\n"
            f"course_name: {course.name}\n"
            f"course_description: {course.description or ''}\n"
            f"existing_knowledge_points: {existing_points}\n"
            "请生成课程知识图谱，importance 只能是 core、important、normal，"
            "mastery 默认 unknown，edge relation 只能是 prerequisite、related、advanced。"
        )
        generated = await self._ai_client.generate_json(
            agent_name="Knowledge Graph Agent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=KNOWLEDGE_GRAPH_SCHEMA,
            use_reasoning=False,
        )
        graph = _normalize_agent_graph(generated, course_id, course.name)
        return await self.save_knowledge_graph(course_id, graph, course_name=course.name)

    async def update_knowledge_graph(
        self,
        course_id: str,
        request: KnowledgeGraphUpdateRequest,
    ) -> dict[str, Any]:
        course_name = await self._resolve_course_name(course_id, request.course_name)
        current_graph = _compact_current_graph(request.current_graph)
        if not current_graph["nodes"]:
            stored_graph = await KnowledgeGraphState.find_one(
                KnowledgeGraphState.graph_id == course_id
            )
            if stored_graph is not None:
                current_graph = {
                    "nodes": stored_graph.nodes,
                    "edges": stored_graph.edges,
                }
        fallback_graph = _fallback_incremental_graph(
            course_id=course_id,
            course_name=course_name,
            current_graph=current_graph,
            request=request,
            updated_reason="Agent update unavailable; kept the current graph and added a small local expansion.",
        )

        system_prompt = (
            "你是 EduAgent Studio 的课程知识图谱更新 Agent。"
            "请在已有图谱基础上做轻量更新，不要完全推翻原图。"
            "优先补充与当前知识点和用户问题相关的 1 到 3 个节点或边，"
            "总节点数控制在 8 到 14 个。"
            "新增节点的名称和描述必须使用中文；专业缩写可以保留，但名称必须同时包含中文。"
            "不要添加与现有节点名称相同或含义重复的节点。只输出合法 JSON。"
        )
        user_prompt = (
            f"course_id: {course_id}\n"
            f"course_name: {course_name}\n"
            f"selected_node_id: {request.selected_node_id or ''}\n"
            f"selected_node_name: {request.selected_node_name or ''}\n"
            f"user_question: {request.user_question or ''}\n"
            f"current_graph: {current_graph}\n"
            "请返回更新后的 nodes、edges 和 updated_reason。"
        )
        system_prompt += (
            "必须保留 current_graph 中所有已有节点和边，只添加与当前节点或用户问题相关的知识点或边。"
            "不得重命名、删除已有节点和边。新增节点 ID 应简短、稳定，并可供前端图谱使用。"
        )
        user_prompt += "\n可以返回完整图谱或仅返回新增节点和边，但不得删除或重命名已有 ID。"

        system_prompt = (
            "You are EduAgent Studio's knowledge graph growth agent. "
            "Only grow outward from the selected node. Return 0 to 2 new nodes, "
            "plus edges that connect the new nodes to the selected node or nearby existing nodes. "
            "Do not rename, delete, or rewrite existing nodes. "
            "New node importance must be core, important, or normal so the UI can keep the same color style. "
            "New node labels must use Chinese characters only; do not use English letters, acronyms, digits, or symbols."
        )
        user_prompt = (
            f"course_id: {course_id}\n"
            f"course_name: {course_name}\n"
            f"selected_node_id: {request.selected_node_id or ''}\n"
            f"selected_node_name: {request.selected_node_name or ''}\n"
            f"user_question: {request.user_question or ''}\n"
            f"current_graph: {current_graph}\n"
            "Return only the new nodes and their new edges. "
            "If no useful expansion exists, return empty nodes and edges."
        )

        try:
            generated = await self._ai_client.generate_json(
                agent_name="Knowledge Graph Update Agent",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=KNOWLEDGE_GRAPH_EXPANSION_SCHEMA,
                use_reasoning=False,
            )
            result = _grow_graph_from_agent(
                payload=generated,
                course_id=course_id,
                course_name=course_name,
                current_graph=current_graph,
                request=request,
            )
        except Exception:
            result = fallback_graph
        return await self.save_knowledge_graph(
            course_id,
            result,
            course_name=course_name,
        )

    async def _resolve_course_name(self, course_id: str, fallback_name: str | None) -> str:
        try:
            course = await Course.get(ObjectId(course_id))
        except Exception:
            course = None
        if course is not None and course.name:
            return course.name
        cleaned = _clean_text(fallback_name)
        return cleaned or "当前课程"

    async def _resolve_notebook_title(self, notebook_id: str) -> str:
        try:
            document = await get_mongo_database()["notebooks"].find_one(
                {"notebook_id": notebook_id},
                {"_id": False, "title": True},
            )
        except Exception:
            return ""
        return _clean_text(document.get("title")) if document else ""

    async def _restore_initial_knowledge_graph(
        self,
        state: KnowledgeGraphState,
    ) -> dict[str, Any]:
        if not state.initial_nodes:
            state.initial_nodes = deepcopy(state.nodes)
            state.initial_edges = deepcopy(state.edges)
        state.nodes = deepcopy(state.initial_nodes)
        state.edges = deepcopy(state.initial_edges)
        state.source = "database"
        state.updated_reason = "Restored initial knowledge graph."
        state.updated_at = datetime.now(UTC)
        await state.save()
        return {
            "course_id": state.graph_id,
            "course_name": state.course_name,
            "nodes": state.nodes,
            "edges": state.edges,
            "source": "database",
            "updated_reason": state.updated_reason,
        }

    @staticmethod
    def _course_to_dict(course: Course) -> dict:
        return {
            "id": str(course.id),
            "name": course.name,
            "description": course.description,
            "teacher_id": str(course.teacher_id) if course.teacher_id else None,
            "created_at": course.created_at,
        }

    @staticmethod
    def _kp_to_dict(kp: KnowledgePoint) -> dict:
        return {
            "id": str(kp.id),
            "course_id": str(kp.course_id),
            "chapter": kp.chapter,
            "name": kp.name,
            "description": kp.description,
            "difficulty": kp.difficulty,
            "prerequisites": [str(pid) for pid in kp.prerequisites],
            "order": kp.order,
            "created_at": kp.created_at,
        }


def _normalize_agent_graph(
    payload: dict[str, Any],
    course_id: str,
    course_name: str,
    current_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_nodes = payload.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise AIServiceError("Knowledge Graph Agent response missing nodes")

    current_nodes = _current_graph_nodes(current_graph or {})
    current_node_by_id = {node["id"]: node for node in current_nodes}
    label_owner_ids = {
        _normalized_label_key(node["label"]): node["id"]
        for node in current_nodes
        if _normalized_label_key(node["label"])
    }
    nodes = []
    seen_node_ids = set()
    node_id_aliases: dict[str, str] = {}
    for index, raw_node in enumerate(raw_nodes[:14]):
        if not isinstance(raw_node, dict):
            continue
        node_id = _clean_node_id(raw_node.get("id"), index)
        existing_node = current_node_by_id.get(node_id)
        label = (
            existing_node["label"]
            if existing_node
            else _clean_chinese_node_label(raw_node.get("label") or raw_node.get("name"))
        )
        if not label:
            continue
        label_key = _normalized_label_key(label)
        duplicate_owner_id = label_owner_ids.get(label_key)
        if not existing_node and duplicate_owner_id:
            node_id_aliases[node_id] = duplicate_owner_id
            continue
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        label_owner_ids.setdefault(label_key, node_id)
        description = (
            existing_node["description"]
            if existing_node
            else _clean_text(raw_node.get("description"))
        )
        if not existing_node and not _contains_chinese(description):
            description = f"梳理{label}的核心概念、适用场景和相关知识。"
        nodes.append(
            _copy_graph_node_layout(
                {
                "id": node_id,
                "label": label,
                "description": description,
                "importance": _normalize_choice(
                    (
                        existing_node["importance"]
                        if existing_node
                        else raw_node.get("importance")
                    ),
                    {"core", "important", "normal"},
                    "normal",
                ),
                "mastery": _normalize_choice(
                    (
                        existing_node["mastery"]
                        if existing_node
                        else raw_node.get("mastery")
                    ),
                    {"unknown", "weak", "medium", "mastered"},
                    "unknown",
                ),
                },
                existing_node or raw_node,
            )
        )

    if not nodes and not current_nodes:
        raise AIServiceError("Knowledge Graph Agent returned no usable nodes")

    node_ids = {node["id"] for node in nodes} | set(current_node_by_id)
    edges = []
    seen_edge_keys = set()
    for index, raw_edge in enumerate(payload.get("edges") or []):
        if not isinstance(raw_edge, dict):
            continue
        source = node_id_aliases.get(
            _clean_text(raw_edge.get("source")),
            _clean_text(raw_edge.get("source")),
        )
        target = node_id_aliases.get(
            _clean_text(raw_edge.get("target")),
            _clean_text(raw_edge.get("target")),
        )
        if source not in node_ids or target not in node_ids or source == target:
            continue
        relation = _normalize_choice(
            raw_edge.get("relation"),
            {"prerequisite", "related", "advanced"},
            "related",
        )
        edge_key = (source, target, relation)
        if edge_key in seen_edge_keys:
            continue
        seen_edge_keys.add(edge_key)
        edges.append(
            {
                "id": f"agent-edge-{index + 1}",
                "source": source,
                "target": target,
                "relation": relation,
                "description": _clean_text(
                    raw_edge.get("description") or raw_edge.get("reason")
                ),
            }
        )

    return {
        "course_id": course_id,
        "course_name": course_name,
        "nodes": nodes,
        "edges": edges,
        "source": "agent",
        "updated_reason": _clean_text(payload.get("updated_reason")),
    }


def _edge_key(edge: dict[str, Any]) -> str:
    return "->".join(
        [
            _clean_text(edge.get("source")),
            _clean_text(edge.get("target")),
            _clean_text(edge.get("relation")) or "related",
        ]
    )


def _attach_graph_delta(
    graph: dict[str, Any],
    current_graph: dict[str, Any],
) -> dict[str, Any]:
    current_nodes = current_graph.get("nodes") if isinstance(current_graph, dict) else []
    current_edges = current_graph.get("edges") if isinstance(current_graph, dict) else []
    current_node_ids = {
        _clean_text(node.get("id"))
        for node in current_nodes
        if isinstance(node, dict) and _clean_text(node.get("id"))
    }
    current_edge_keys = {
        _edge_key(edge)
        for edge in current_edges
        if isinstance(edge, dict) and _edge_key(edge)
    }

    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    graph["added_node_ids"] = [
        node["id"]
        for node in nodes
        if isinstance(node, dict) and node.get("id") not in current_node_ids
    ]
    graph["updated_node_ids"] = [
        node["id"]
        for node in nodes
        if isinstance(node, dict) and node.get("id") in current_node_ids
    ]
    graph["added_edge_ids"] = [
        _clean_text(edge.get("id")) or f"{edge.get('source')}-{edge.get('target')}"
        for edge in edges
        if isinstance(edge, dict) and _edge_key(edge) not in current_edge_keys
    ]
    return graph


def _grow_graph_from_agent(
    payload: dict[str, Any],
    course_id: str,
    course_name: str,
    current_graph: dict[str, Any],
    request: KnowledgeGraphUpdateRequest,
) -> dict[str, Any]:
    current_nodes = _current_graph_nodes(current_graph)
    current_edges = _current_graph_edges(current_graph)
    if not current_nodes:
        return _attach_graph_delta(
            _fallback_graph_for_course(
                course_id,
                course_name,
                "Current graph was empty; restored a starter graph.",
            ),
            {"nodes": [], "edges": []},
        )

    selected_node_id = _clean_text(request.selected_node_id) or current_nodes[0]["id"]
    selected_node = next(
        (node for node in current_nodes if node["id"] == selected_node_id),
        current_nodes[0],
    )
    selected_node_id = selected_node["id"]

    existing_ids = {node["id"] for node in current_nodes}
    existing_label_keys = {
        _normalized_label_key(node["label"])
        for node in current_nodes
        if _normalized_label_key(node["label"])
    }
    node_id_aliases: dict[str, str] = {}
    new_nodes: list[dict[str, Any]] = []

    raw_nodes = payload.get("nodes") if isinstance(payload, dict) else []
    for index, raw_node in enumerate(raw_nodes if isinstance(raw_nodes, list) else []):
        if not isinstance(raw_node, dict):
            continue
        raw_node_id = _clean_node_id(raw_node.get("id"), index)
        if raw_node_id in existing_ids:
            node_id_aliases[raw_node_id] = raw_node_id
            continue
        node_id = raw_node_id
        label = _clean_chinese_node_label(raw_node.get("label") or raw_node.get("name"))
        if not label:
            continue
        label_key = _normalized_label_key(label)
        if not label_key or label_key in existing_label_keys:
            continue
        if node_id in existing_ids:
            node_id = _clean_node_id(f"{selected_node_id}-{node_id}", index)
        if node_id in existing_ids:
            continue
        description = _clean_text(raw_node.get("description"))
        if not description:
            description = f"围绕{selected_node['label']}进一步展开{label}的概念、方法和应用。"
        node = {
            "id": node_id,
            "label": label,
            "description": description,
            "importance": _normalize_choice(
                raw_node.get("importance"),
                {"core", "important", "normal"},
                "normal",
            ),
            "mastery": "unknown",
        }
        existing_ids.add(node_id)
        existing_label_keys.add(label_key)
        node_id_aliases[raw_node_id] = node_id
        new_nodes.append(node)
        if len(new_nodes) >= 2:
            break

    new_node_ids = {node["id"] for node in new_nodes}
    valid_node_ids = {node["id"] for node in current_nodes} | new_node_ids
    seen_edge_keys = {
        _edge_key(edge)
        for edge in current_edges
        if _edge_key(edge)
    }
    new_edges: list[dict[str, Any]] = []
    raw_edges = payload.get("edges") if isinstance(payload, dict) else []
    for index, raw_edge in enumerate(raw_edges if isinstance(raw_edges, list) else []):
        if not isinstance(raw_edge, dict):
            continue
        source = node_id_aliases.get(
            _clean_text(raw_edge.get("source")),
            _clean_text(raw_edge.get("source")),
        )
        target = node_id_aliases.get(
            _clean_text(raw_edge.get("target")),
            _clean_text(raw_edge.get("target")),
        )
        if source not in valid_node_ids or target not in valid_node_ids or source == target:
            continue
        if source not in new_node_ids and target not in new_node_ids:
            continue
        relation = _normalize_choice(
            raw_edge.get("relation"),
            {"prerequisite", "related", "advanced"},
            "related",
        )
        edge = {
            "id": _clean_text(raw_edge.get("id")) or f"agent-growth-edge-{index + 1}",
            "source": source,
            "target": target,
            "relation": relation,
            "description": _clean_text(raw_edge.get("description") or raw_edge.get("reason")),
        }
        edge_key = _edge_key(edge)
        if not edge_key or edge_key in seen_edge_keys:
            continue
        seen_edge_keys.add(edge_key)
        new_edges.append(edge)

    connected_new_node_ids = {
        edge["source"] if edge["source"] in new_node_ids else edge["target"]
        for edge in new_edges
        if edge["source"] in new_node_ids or edge["target"] in new_node_ids
    }
    for node in new_nodes:
        if node["id"] in connected_new_node_ids:
            continue
        edge = {
            "id": f"agent-growth-selected-edge-{len(new_edges) + 1}",
            "source": selected_node_id,
            "target": node["id"],
            "relation": "advanced",
            "description": f"{node['label']}是{selected_node['label']}的进一步拓展。",
        }
        edge_key = _edge_key(edge)
        if edge_key and edge_key not in seen_edge_keys:
            seen_edge_keys.add(edge_key)
            new_edges.append(edge)

    return _attach_graph_delta(
        {
            "course_id": course_id,
            "course_name": course_name,
            "nodes": current_nodes + new_nodes,
            "edges": current_edges + new_edges,
            "source": "agent",
            "updated_reason": _clean_text(payload.get("updated_reason"))
            or "Expanded from the selected knowledge node.",
        },
        current_graph,
    )


def _current_graph_nodes(current_graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = current_graph.get("nodes") if isinstance(current_graph, dict) else []
    result = []
    for index, node in enumerate(nodes if isinstance(nodes, list) else []):
        if not isinstance(node, dict):
            continue
        node_id = _clean_text(node.get("id")) or f"current-node-{index + 1}"
        label = _clean_text(node.get("label") or node.get("name")) or node_id
        result.append(
            _copy_graph_node_layout(
                {
                "id": node_id,
                "label": label,
                "description": _clean_text(node.get("description")),
                "importance": _normalize_choice(
                    node.get("importance"),
                    {"core", "important", "normal"},
                    "normal",
                ),
                "mastery": _normalize_choice(
                    node.get("mastery"),
                    {"unknown", "weak", "medium", "mastered"},
                    "unknown",
                ),
                },
                node,
            )
        )
    return result


def _current_graph_edges(current_graph: dict[str, Any]) -> list[dict[str, Any]]:
    edges = current_graph.get("edges") if isinstance(current_graph, dict) else []
    result = []
    for index, edge in enumerate(edges if isinstance(edges, list) else []):
        if not isinstance(edge, dict):
            continue
        source = _clean_text(edge.get("source"))
        target = _clean_text(edge.get("target"))
        if not source or not target or source == target:
            continue
        result.append(
            {
                "id": _clean_text(edge.get("id")) or f"current-edge-{index + 1}",
                "source": source,
                "target": target,
                "relation": _normalize_choice(
                    edge.get("relation"),
                    {"prerequisite", "related", "advanced"},
                    "related",
                ),
                "description": _clean_text(edge.get("description") or edge.get("reason")),
            }
        )
    return result


def _fallback_expansion_templates(
    course_name: str,
    selected_node_id: str,
    selected_node_name: str,
    user_question: str,
) -> list[dict[str, Any]]:
    text = f"{course_name} {selected_node_id} {selected_node_name} {user_question}".lower()
    if "tcp" in text:
        return [
            {"id": "reliable-transport", "label": "TCP 可靠传输", "description": "理解确认、超时、重传和有序字节流交付机制。", "importance": "important"},
            {"id": "congestion-window", "label": "拥塞窗口", "description": "理解慢启动、拥塞避免和快速恢复过程。", "importance": "important"},
            {"id": "tcp-handshake", "label": "TCP 三次握手", "description": "理解连接建立、序列号和状态转换。", "importance": "normal"},
        ]
    if "dns" in text or "\u57df\u540d" in text:
        return [
            {"id": "recursive-resolution", "label": "DNS 递归解析", "description": "理解解析器、根服务器、顶级域和权威服务器的查询链路。", "importance": "important"},
            {"id": "dns-records", "label": "DNS 资源记录", "description": "掌握 A、AAAA、CNAME、MX、TXT 和 NS 等记录。", "importance": "normal"},
            {"id": "dns-cache", "label": "DNS 缓存", "description": "理解生存时间、缓存命中和过期记录排查。", "importance": "normal"},
        ]
    if "virtual" in text or "memory" in text or "\u865a\u62df\u5185\u5b58" in text:
        return [
            {"id": "page-fault", "label": "缺页异常", "description": "理解缺页触发、操作系统处理和指令重启流程。", "importance": "important"},
            {"id": "tlb", "label": "地址转换后备缓冲器（TLB）", "description": "理解地址转换缓存及其对访存延迟的影响。", "importance": "normal"},
            {"id": "working-set", "label": "工作集", "description": "从局部性角度理解活跃页面和抖动风险。", "importance": "normal"},
        ]
    if "deadlock" in text or "\u6b7b\u9501" in text:
        return [
            {"id": "banker-algorithm", "label": "银行家算法", "description": "通过安全状态检查实现死锁避免。", "importance": "important"},
            {"id": "wait-for-graph", "label": "资源等待图", "description": "通过进程和资源之间的环路检测死锁。", "importance": "normal"},
            {"id": "deadlock-prevention", "label": "死锁预防", "description": "通过破坏死锁必要条件来预防死锁。", "importance": "normal"},
        ]
    if "tree" in text or "\u6811" in text:
        return [
            {"id": "tree-traversal", "label": "树的遍历", "description": "掌握前序、中序、后序和层序遍历。", "importance": "important"},
            {"id": "binary-search-tree", "label": "二叉搜索树", "description": "理解有序树操作和结构退化风险。", "importance": "important"},
            {"id": "balanced-tree", "label": "平衡树", "description": "理解 AVL 树和红黑树保障查找效率的动机。", "importance": "normal"},
        ]
    if "sort" in text or "\u6392\u5e8f" in text:
        return [
            {"id": "quick-sort", "label": "快速排序", "description": "理解分区、基准选择和平均时间复杂度。", "importance": "important"},
            {"id": "merge-sort", "label": "归并排序", "description": "理解分治排序和稳定合并过程。", "importance": "important"},
            {"id": "sort-stability", "label": "排序稳定性", "description": "理解相同关键字记录保持相对顺序的意义。", "importance": "normal"},
        ]
    return [
        {"id": "concept-boundary", "label": "概念边界", "description": f"梳理{selected_node_name or '当前知识点'}的适用范围和常见误区。", "importance": "normal"},
        {"id": "practice-case", "label": "练习案例", "description": f"通过小型应用场景检验对{selected_node_name or '当前知识点'}的理解。", "importance": "normal"},
    ]


def _fallback_incremental_graph(
    course_id: str,
    course_name: str,
    current_graph: dict[str, Any],
    request: KnowledgeGraphUpdateRequest,
    updated_reason: str,
) -> dict[str, Any]:
    current_nodes = _current_graph_nodes(current_graph)
    current_edges = _current_graph_edges(current_graph)
    if not current_nodes:
        return _attach_graph_delta(
            _fallback_graph_for_course(course_id, course_name, updated_reason),
            {"nodes": [], "edges": []},
        )

    selected_node_id = _clean_text(request.selected_node_id) or current_nodes[0]["id"]
    selected_node = next(
        (node for node in current_nodes if node["id"] == selected_node_id),
        current_nodes[0],
    )
    selected_node_name = _clean_text(request.selected_node_name) or selected_node["label"]
    existing_ids = {node["id"] for node in current_nodes}
    existing_label_keys = {
        _normalized_label_key(node["label"])
        for node in current_nodes
        if _normalized_label_key(node["label"])
    }
    new_nodes = []

    for template in _fallback_expansion_templates(
        _canonical_course_name(course_name),
        selected_node_id,
        selected_node_name,
        _clean_text(request.user_question),
    ):
        label = _clean_chinese_node_label(template["label"])
        if not label:
            continue
        node_id = _clean_node_id(template["id"], len(new_nodes))
        if node_id in existing_ids:
            node_id = _clean_node_id(f"{selected_node_id}-{node_id}", len(new_nodes))
        if node_id in existing_ids:
            continue
        label_key = _normalized_label_key(label)
        if not label_key or label_key in existing_label_keys:
            continue
        existing_ids.add(node_id)
        existing_label_keys.add(label_key)
        new_nodes.append(
            {
                "id": node_id,
                "label": label,
                "description": template["description"],
                "importance": _normalize_choice(
                    template.get("importance"),
                    {"core", "important", "normal"},
                    "normal",
                ),
                "mastery": "unknown",
            }
        )
        if len(new_nodes) >= 2:
            break

    new_edges = [
        {
            "id": f"fallback-update-edge-{index + 1}",
            "source": selected_node_id,
            "target": node["id"],
            "relation": "advanced" if index == 0 else "related",
            "description": f"{node['label']}是{selected_node_name}的进一步拓展。",
        }
        for index, node in enumerate(new_nodes)
        if node["id"] != selected_node_id
    ]

    return _attach_graph_delta(
        {
            "course_id": course_id,
            "course_name": course_name,
            "nodes": current_nodes + new_nodes,
            "edges": current_edges + new_edges,
            "source": "fallback",
            "updated_reason": updated_reason,
        },
        current_graph,
    )


def _fallback_graph_for_course(
    course_id: str,
    course_name: str,
    updated_reason: str = "",
) -> dict[str, Any]:
    canonical_name = _canonical_course_name(course_name)
    template = FALLBACK_GRAPHS.get(canonical_name)
    if template is None:
        topic = course_name or "\u5f53\u524d\u8bfe\u7a0b"
        template = {
            "nodes": [
                {
                    "id": "course-overview",
                    "label": "\u8bfe\u7a0b\u603b\u89c8",
                    "description": f"\u68b3\u7406{topic}\u7684\u5b66\u4e60\u76ee\u6807\u3001\u4e3b\u7ebf\u548c\u8bc4\u4f30\u8981\u6c42\u3002",
                    "importance": "core",
                },
                {
                    "id": "prerequisite-map",
                    "label": "\u5148\u4fee\u77e5\u8bc6",
                    "description": "\u8865\u9f50\u8bfe\u7a0b\u6240\u9700\u7684\u57fa\u7840\u6982\u5ff5\u548c\u5de5\u5177\u65b9\u6cd5\u3002",
                    "importance": "important",
                },
                {
                    "id": "core-concepts",
                    "label": "\u6838\u5fc3\u6982\u5ff5",
                    "description": "\u805a\u7126\u8bfe\u7a0b\u4e2d\u9ad8\u9891\u3001\u9ad8\u5173\u8054\u7684\u5173\u952e\u77e5\u8bc6\u70b9\u3002",
                    "importance": "core",
                },
                {
                    "id": "practice-loop",
                    "label": "\u7ec3\u4e60\u4e0e\u53cd\u9988",
                    "description": "\u901a\u8fc7\u9898\u76ee\u3001\u5b9e\u9a8c\u6216\u6848\u4f8b\u9a8c\u8bc1\u7406\u89e3\u5e76\u4fee\u6b63\u8bef\u533a\u3002",
                    "importance": "important",
                },
                {
                    "id": "summary-review",
                    "label": "\u603b\u7ed3\u590d\u76d8",
                    "description": "\u5efa\u7acb\u77e5\u8bc6\u70b9\u95f4\u7684\u8054\u7cfb\uff0c\u5f62\u6210\u53ef\u8fc1\u79fb\u7684\u89e3\u9898\u601d\u8def\u3002",
                    "importance": "normal",
                },
            ],
            "edges": [
                {
                    "source": "course-overview",
                    "target": "prerequisite-map",
                    "relation": "prerequisite",
                    "description": "\u5148\u660e\u786e\u8bfe\u7a0b\u4e3b\u7ebf\uff0c\u518d\u68b3\u7406\u5148\u4fee\u80fd\u529b\u3002",
                },
                {
                    "source": "prerequisite-map",
                    "target": "core-concepts",
                    "relation": "prerequisite",
                    "description": "\u5148\u4fee\u57fa\u7840\u652f\u6491\u6838\u5fc3\u6982\u5ff5\u5b66\u4e60\u3002",
                },
                {
                    "source": "core-concepts",
                    "target": "practice-loop",
                    "relation": "related",
                    "description": "\u7ec3\u4e60\u7528\u4e8e\u68c0\u9a8c\u6838\u5fc3\u6982\u5ff5\u7684\u7406\u89e3\u3002",
                },
                {
                    "source": "practice-loop",
                    "target": "summary-review",
                    "relation": "advanced",
                    "description": "\u5c06\u7ec3\u4e60\u53cd\u9988\u56de\u6536\u5230\u590d\u76d8\u4e0e\u77e5\u8bc6\u7f51\u7edc\u4e2d\u3002",
                },
            ],
        }
    nodes = []
    seen_label_keys = set()
    for node in template["nodes"]:
        label = _clean_chinese_node_label(node.get("label"))
        label_key = _normalized_label_key(label)
        if not label or not label_key or label_key in seen_label_keys:
            continue
        seen_label_keys.add(label_key)
        nodes.append(
            {
                **node,
                "label": label,
                "mastery": "unknown",
            }
        )
    node_ids = {node["id"] for node in nodes}

    return {
        "course_id": course_id,
        "course_name": course_name,
        "nodes": nodes,
        "edges": [
            {
                "id": f"fallback-edge-{index + 1}",
                **edge,
            }
            for index, edge in enumerate(template["edges"])
            if edge["source"] in node_ids and edge["target"] in node_ids
        ],
        "source": "fallback",
        "updated_reason": updated_reason,
    }


def _canonical_course_name(course_name: str | None) -> str:
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
    return text


def _compact_current_graph(current_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = current_graph.get("nodes") if isinstance(current_graph, dict) else []
    edges = current_graph.get("edges") if isinstance(current_graph, dict) else []
    return {
        "nodes": nodes[:14] if isinstance(nodes, list) else [],
        "edges": edges[:24] if isinstance(edges, list) else [],
    }


def _copy_graph_node_layout(
    target: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    chapter = _clean_text(source.get("chapter"))
    if chapter:
        target["chapter"] = chapter
    order = source.get("order")
    if isinstance(order, int) and not isinstance(order, bool):
        target["order"] = order
    for coordinate in ("x", "y"):
        value = source.get(coordinate)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            target[coordinate] = float(value)
    return target


def _graph_for_storage(
    graph_id: str,
    course_name: str | None,
    graph: dict[str, Any],
) -> dict[str, Any]:
    nodes = _current_graph_nodes(graph)[:16]
    node_ids = {node["id"] for node in nodes}
    edges = [
        edge
        for edge in _current_graph_edges(graph)[:28]
        if edge["source"] in node_ids and edge["target"] in node_ids
    ]
    return {
        "course_id": graph_id,
        "course_name": _clean_text(course_name or graph.get("course_name")) or "当前课程",
        "nodes": nodes,
        "edges": edges,
        "source": _clean_text(graph.get("source")) or "database",
        "updated_reason": _clean_text(graph.get("updated_reason")),
    }


def _clean_node_id(value: Any, index: int) -> str:
    cleaned = _clean_text(value)
    if cleaned:
        return cleaned.replace(" ", "-")[:64]
    return f"agent-node-{index + 1}"


def _clean_chinese_node_label(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    normalized = raw.upper().replace(" ", "")
    replacement = CHINESE_NODE_LABEL_REPLACEMENTS.get(normalized)
    if replacement:
        return replacement
    chinese_label = "".join(
        character
        for character in raw
        if _is_chinese_character(character)
    )
    if chinese_label:
        return chinese_label[:24]
    for key, replacement in CHINESE_NODE_LABEL_REPLACEMENTS.items():
        if key in normalized:
            return replacement
    return ""


def _normalize_choice(value: Any, allowed: set[str], fallback: str) -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in allowed else fallback


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _is_chinese_character(character: str) -> bool:
    return "\u3400" <= character <= "\u9fff"


def _contains_chinese(value: Any) -> bool:
    return any(_is_chinese_character(character) for character in _clean_text(value))


def _normalized_label_key(value: Any) -> str:
    chinese_label = _clean_chinese_node_label(value)
    if chinese_label:
        return chinese_label.lower()
    return "".join(
        character.lower()
        for character in _clean_text(value)
        if character.isalnum()
    )
