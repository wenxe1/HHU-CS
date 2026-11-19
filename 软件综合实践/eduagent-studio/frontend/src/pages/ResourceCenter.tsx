import {
  BotMessageSquare,
  Maximize2,
  Minimize2,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
} from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent,
  type WheelEvent,
} from 'react'
import ReactMarkdown from 'react-markdown'
import { useOutletContext } from 'react-router'
import remarkGfm from 'remark-gfm'
import {
  classroomApi,
  courseApi,
  tutorApi,
  type CourseSummary,
  type KnowledgeGraphEdge,
  type KnowledgeGraphNode,
  type KnowledgeGraphResponse,
  type NotebookSummary,
  type ResourceRecommendation,
  type UserProfileLearningResource,
} from '../lib/api'
import { getActiveUserId } from '../lib/auth'
import {
  useNotebookSessionState,
  useNotebookVisitId,
} from '../layouts/NotebookSessionContext'

type GraphImportance = 'core' | 'important' | 'normal'
type GraphMastery = 'unknown' | 'weak' | 'medium' | 'mastered'
type ChatRole = 'user' | 'assistant'

interface GraphNode {
  id: string
  label: string
  description: string
  chapter: string
  importance: GraphImportance
  mastery: GraphMastery
  order: number
  x: number
  y: number
}

interface GraphEdge {
  id: string
  source: string
  target: string
  relation: string
  description: string
}

interface GraphDataset {
  nodes: GraphNode[]
  edges: GraphEdge[]
  source: 'database' | 'agent' | 'fallback' | 'local'
}

interface NodeTooltip {
  type: 'node'
  node: GraphNode
  x: number
  y: number
}

interface EdgeTooltip {
  type: 'edge'
  edge: GraphEdge
  source: GraphNode
  target: GraphNode
  x: number
  y: number
}

type GraphTooltip = NodeTooltip | EdgeTooltip

interface ChatMessage {
  id: string
  role: ChatRole
  content: string
}

interface DragState {
  mode: 'pan' | 'node'
  nodeId?: string
  hasDragged?: boolean
  startClientX: number
  startClientY: number
  startTranslateX: number
  startTranslateY: number
  startNodeX?: number
  startNodeY?: number
}

interface NodeVelocity {
  vx: number
  vy: number
}

const FALLBACK_COURSES: CourseSummary[] = [
  {
    id: 'demo-data-structures',
    name: '数据结构',
    description: '数据结构课程图谱',
  },
  {
    id: 'demo-computer-organization',
    name: '计算机组成原理',
    description: '计算机组成原理课程图谱',
  },
  {
    id: 'demo-operating-system',
    name: '操作系统',
    description: '操作系统课程图谱',
  },
  {
    id: 'demo-computer-network',
    name: '计算机网络',
    description: '计算机网络课程图谱',
  },
]

const DEMO_COURSE = FALLBACK_COURSES[0]

function createFallbackGraph(
  course: CourseSummary,
  nodes: Array<{
    id: string
    label: string
    description: string
    importance: GraphImportance
    mastery?: GraphMastery
  }>,
  edges: Array<{ source: string; target: string; relation?: string; description?: string }>,
): KnowledgeGraphResponse {
  return {
    course_id: course.id,
    course_name: course.name,
    source: 'local',
    nodes: nodes.map((node) => ({
      ...node,
      mastery: 'unknown',
    })),
    edges,
  }
}

const FALLBACK_GRAPHS_BY_COURSE: Record<string, KnowledgeGraphResponse> = {
  数据结构: createFallbackGraph(
    FALLBACK_COURSES[0],
    [
    {
      id: 'complexity',
      label: '算法复杂度分析',
      description: '衡量算法时间和空间效率的基础方法，是后续结构选择与算法比较的依据。',
      importance: 'core',
      mastery: 'unknown',
    },
    {
      id: 'linear-list',
      label: '线性表',
      description: '理解顺序存储和链式存储，掌握插入、删除、查找的代价。',
      importance: 'core',
      mastery: 'unknown',
    },
    {
      id: 'stack-queue',
      label: '栈与队列',
      description: '掌握 LIFO/FIFO 模型，并应用于表达式求值、递归模拟和层次遍历。',
      importance: 'important',
      mastery: 'unknown',
    },
    {
      id: 'tree',
      label: '树与二叉树',
      description: '理解树的递归结构、二叉树性质和先中后序遍历。',
      importance: 'core',
      mastery: 'unknown',
    },
    {
      id: 'binary-search-tree',
      label: '二叉搜索树',
      description: '掌握 BST 查找、插入、删除，以及退化风险。',
      importance: 'important',
      mastery: 'unknown',
    },
    {
      id: 'graph',
      label: '图结构',
      description: '理解邻接矩阵、邻接表、DFS、BFS 和连通性分析。',
      importance: 'core',
      mastery: 'unknown',
    },
    {
      id: 'sort-search',
      label: '查找与排序',
      description: '掌握二分查找、快速排序、归并排序等常用算法。',
      importance: 'important',
      mastery: 'unknown',
    },
    {
      id: 'hashing',
      label: '散列结构',
      description: '理解哈希函数、冲突处理和平均复杂度分析。',
      importance: 'normal',
    },
  ],
    [
    { source: 'complexity', target: 'linear-list', relation: 'prerequisite' },
    { source: 'linear-list', target: 'stack-queue', relation: 'prerequisite' },
    { source: 'stack-queue', target: 'tree', relation: 'prerequisite' },
    { source: 'tree', target: 'binary-search-tree', relation: 'advanced' },
    { source: 'stack-queue', target: 'graph', relation: 'prerequisite' },
    { source: 'complexity', target: 'sort-search', relation: 'related' },
    { source: 'linear-list', target: 'hashing', relation: 'related' },
  ],
  ),
  计算机组成原理: createFallbackGraph(
    FALLBACK_COURSES[1],
    [
      {
        id: 'data-representation',
        label: '数据表示',
        description: '理解二进制、补码、浮点数和字符编码，是分析硬件执行数据的入口。',
        importance: 'core',
      },
      {
        id: 'alu',
        label: '运算器',
        description: '掌握算术逻辑单元、加法器和状态标志，理解指令执行中的运算过程。',
        importance: 'important',
      },
      {
        id: 'memory-system',
        label: '存储系统',
        description: '理解寄存器、Cache、主存与外存的层次结构和局部性原理。',
        importance: 'core',
      },
      {
        id: 'instruction-system',
        label: '指令系统',
        description: '掌握指令格式、寻址方式和机器级程序的基本执行模型。',
        importance: 'important',
      },
      {
        id: 'cpu',
        label: 'CPU',
        description: '理解控制器、数据通路、流水线和中断对处理器工作的影响。',
        importance: 'core',
      },
      {
        id: 'bus-io',
        label: '总线与 I/O',
        description: '理解总线通信、接口、中断和 DMA 在输入输出系统中的作用。',
        importance: 'normal',
      },
    ],
    [
      { source: 'data-representation', target: 'alu', relation: 'prerequisite' },
      { source: 'data-representation', target: 'memory-system', relation: 'related' },
      { source: 'alu', target: 'instruction-system', relation: 'related' },
      { source: 'instruction-system', target: 'cpu', relation: 'prerequisite' },
      { source: 'memory-system', target: 'cpu', relation: 'prerequisite' },
      { source: 'cpu', target: 'bus-io', relation: 'related' },
    ],
  ),
  操作系统: createFallbackGraph(
    FALLBACK_COURSES[2],
    [
      {
        id: 'process-thread',
        label: '进程与线程',
        description: '理解进程、线程、上下文切换和资源隔离，是学习操作系统并发模型的基础。',
        importance: 'core',
      },
      {
        id: 'cpu-scheduling',
        label: '处理机调度',
        description: '掌握先来先服务、时间片轮转、优先级等调度策略及其指标。',
        importance: 'important',
      },
      {
        id: 'sync-mutual-exclusion',
        label: '同步与互斥',
        description: '理解临界区、信号量、管程和并发协作中的正确性问题。',
        importance: 'core',
      },
      {
        id: 'memory-management',
        label: '内存管理',
        description: '掌握分页、分段、虚拟内存和页面置换的基本机制。',
        importance: 'core',
      },
      {
        id: 'file-system',
        label: '文件系统',
        description: '理解文件目录、索引分配、磁盘调度和持久化组织方式。',
        importance: 'important',
      },
      {
        id: 'deadlock',
        label: '死锁',
        description: '掌握死锁产生条件、预防、避免和检测恢复策略。',
        importance: 'normal',
      },
    ],
    [
      { source: 'process-thread', target: 'cpu-scheduling', relation: 'prerequisite' },
      { source: 'process-thread', target: 'sync-mutual-exclusion', relation: 'prerequisite' },
      { source: 'sync-mutual-exclusion', target: 'deadlock', relation: 'advanced' },
      { source: 'process-thread', target: 'memory-management', relation: 'related' },
      { source: 'memory-management', target: 'file-system', relation: 'related' },
      { source: 'cpu-scheduling', target: 'deadlock', relation: 'related' },
    ],
  ),
  计算机网络: createFallbackGraph(
    FALLBACK_COURSES[3],
    [
      {
        id: 'tcp-ip-model',
        label: 'OSI/TCP-IP 模型',
        description: '理解分层思想、协议栈职责和数据封装，是学习网络协议的总览框架。',
        importance: 'core',
      },
      {
        id: 'data-link-layer',
        label: '数据链路层',
        description: '掌握成帧、差错检测、MAC 地址和局域网访问控制。',
        importance: 'important',
      },
      {
        id: 'network-layer',
        label: '网络层',
        description: '理解 IP 地址、子网划分、转发与路由选择机制。',
        importance: 'core',
      },
      {
        id: 'transport-layer',
        label: '传输层',
        description: '掌握 TCP/UDP、可靠传输、流量控制和拥塞控制。',
        importance: 'core',
      },
      {
        id: 'application-layer',
        label: '应用层',
        description: '理解 HTTP、DNS、邮件等应用协议如何使用传输层服务。',
        importance: 'important',
      },
      {
        id: 'routing-congestion',
        label: '路由与拥塞控制',
        description: '理解路由算法、拥塞窗口和网络性能调节策略。',
        importance: 'normal',
      },
    ],
    [
      { source: 'tcp-ip-model', target: 'data-link-layer', relation: 'prerequisite' },
      { source: 'data-link-layer', target: 'network-layer', relation: 'prerequisite' },
      { source: 'network-layer', target: 'transport-layer', relation: 'prerequisite' },
      { source: 'transport-layer', target: 'application-layer', relation: 'prerequisite' },
      { source: 'network-layer', target: 'routing-congestion', relation: 'advanced' },
      { source: 'transport-layer', target: 'routing-congestion', relation: 'related' },
    ],
  ),
}

const DEMO_GRAPH = FALLBACK_GRAPHS_BY_COURSE[DEMO_COURSE.name]

const LOCAL_RECOMMENDATIONS: ResourceRecommendation[] = [
  {
    id: 'open-data-structures',
    title: 'Open Data Structures',
    authors: ['Pat Morin'],
    source: 'opendatastructures.org',
    cover_url: '',
    description: '开放教材，系统覆盖常见数据结构。',
    level: '入门',
    tags: ['数据结构'],
    related_knowledge_points: ['数据结构'],
    reason: '适合作为课程基础教材。',
    url: 'https://opendatastructures.org/',
  },
  {
    id: 'mit-6006',
    title: 'MIT OCW 6.006 Introduction to Algorithms',
    authors: ['MIT OpenCourseWare'],
    source: 'MIT OCW',
    cover_url: '',
    description: 'MIT 公开课，覆盖算法分析与常见数据结构。',
    level: '进阶',
    tags: ['算法'],
    related_knowledge_points: ['算法复杂度分析'],
    reason: '适合结合公开课讲义学习。',
    url: 'https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/',
  },
  {
    id: 'visualgo',
    title: 'VisuAlgo',
    authors: ['VisuAlgo Team'],
    source: 'visualgo.net',
    cover_url: '',
    description: '交互式算法可视化平台。',
    level: '入门',
    tags: ['可视化'],
    related_knowledge_points: ['树与图'],
    reason: '适合演示结构变化过程。',
    url: 'https://visualgo.net/en',
  },
  {
    id: 'cp-algorithms',
    title: 'CP-Algorithms',
    authors: ['CP-Algorithms contributors'],
    source: 'cp-algorithms.com',
    cover_url: '',
    description: '开源算法资料库。',
    level: '实战',
    tags: ['算法实现'],
    related_knowledge_points: ['查找与排序'],
    reason: '适合查看高质量代码实现。',
    url: 'https://cp-algorithms.com/',
  },
  {
    id: 'opendsa',
    title: 'OpenDSA eTextbook',
    authors: ['OpenDSA Project'],
    source: 'OpenDSA',
    cover_url: '',
    description: '开放交互式电子教材。',
    level: '进阶',
    tags: ['电子教材'],
    related_knowledge_points: ['数据结构'],
    reason: '适合配合交互练习学习。',
    url: 'https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/',
  },
  {
    id: 'python-data-structures',
    title: 'Python Tutorial: Data Structures',
    authors: ['Python Software Foundation'],
    source: 'docs.python.org',
    cover_url: '',
    description: 'Python 官方数据结构教程。',
    level: '入门',
    tags: ['官方文档'],
    related_knowledge_points: ['线性表'],
    reason: '适合用代码巩固基础结构。',
    url: 'https://docs.python.org/3/tutorial/datastructures.html',
  },
]

const COURSE_RECOMMENDATIONS_BY_NAME: Record<string, ResourceRecommendation[]> = {
  数据结构: LOCAL_RECOMMENDATIONS,
  计算机组成原理: [
    {
      id: 'csapp',
      title: 'Computer Systems: A Programmer’s Perspective',
      authors: ['Randal E. Bryant', 'David R. O’Hallaron'],
      source: 'CS:APP',
      cover_url: '',
      description: '从程序员视角串联数据表示、存储层次、链接和系统执行。',
      level: '进阶',
      tags: ['计算机组成原理'],
      related_knowledge_points: ['CPU'],
      reason: '适合理解硬件结构与程序执行之间的关系。',
      url: 'https://csapp.cs.cmu.edu/',
    },
    {
      id: 'nand2tetris',
      title: 'Nand2Tetris',
      authors: ['Noam Nisan', 'Shimon Schocken'],
      source: 'nand2tetris.org',
      cover_url: '',
      description: '用项目方式从逻辑门搭建到计算机系统。',
      level: '入门',
      tags: ['硬件系统'],
      related_knowledge_points: ['运算器'],
      reason: '适合用动手实验建立组成原理直觉。',
      url: 'https://www.nand2tetris.org/',
    },
    {
      id: 'patterson-hennessy',
      title: 'Computer Organization and Design',
      authors: ['David A. Patterson', 'John L. Hennessy'],
      source: 'Morgan Kaufmann',
      cover_url: '',
      description: '经典组成原理教材，覆盖指令系统、处理器和存储层次。',
      level: '进阶',
      tags: ['体系结构'],
      related_knowledge_points: ['指令系统'],
      reason: '适合作为课程主线参考资料。',
      url: 'https://www.elsevier.com/books/computer-organization-and-design-risc-v-edition/patterson/978-0-12-820331-6',
    },
    {
      id: 'riscv-reader',
      title: 'The RISC-V Reader',
      authors: ['David Patterson', 'Andrew Waterman'],
      source: 'RISC-V',
      cover_url: '',
      description: '围绕 RISC-V 指令集理解现代处理器指令设计。',
      level: '实战',
      tags: ['指令集'],
      related_knowledge_points: ['指令系统'],
      reason: '适合补充机器指令与数据通路知识。',
      url: 'http://www.riscvbook.com/',
    },
  ],
  操作系统: [
    {
      id: 'ostep',
      title: 'Operating Systems: Three Easy Pieces',
      authors: ['Remzi H. Arpaci-Dusseau', 'Andrea C. Arpaci-Dusseau'],
      source: 'OSTEP',
      cover_url: '',
      description: '开放教材，系统覆盖虚拟化、并发和持久化。',
      level: '入门',
      tags: ['操作系统'],
      related_knowledge_points: ['进程与线程'],
      reason: '适合沿课程章节逐步建立 OS 核心概念。',
      url: 'https://pages.cs.wisc.edu/~remzi/OSTEP/',
    },
    {
      id: 'mit-6828',
      title: 'MIT 6.828 Operating System Engineering',
      authors: ['MIT'],
      source: 'MIT OCW',
      cover_url: '',
      description: '通过 xv6 实验理解内核、进程、内存和文件系统。',
      level: '实战',
      tags: ['内核实验'],
      related_knowledge_points: ['内存管理'],
      reason: '适合把抽象机制落到代码实现。',
      url: 'https://pdos.csail.mit.edu/6.828/',
    },
    {
      id: 'os-dev',
      title: 'OSDev Wiki',
      authors: ['OSDev Community'],
      source: 'OSDev',
      cover_url: '',
      description: '面向操作系统开发的实践资料和机制说明。',
      level: '进阶',
      tags: ['系统开发'],
      related_knowledge_points: ['文件系统'],
      reason: '适合补充底层实现细节。',
      url: 'https://wiki.osdev.org/',
    },
    {
      id: 'linux-insides',
      title: 'Linux Insides',
      authors: ['0xAX'],
      source: 'GitBook',
      cover_url: '',
      description: '从源码角度拆解 Linux 内核启动、内存和中断机制。',
      level: '进阶',
      tags: ['Linux 内核'],
      related_knowledge_points: ['同步与互斥'],
      reason: '适合进阶理解真实系统实现。',
      url: 'https://0xax.gitbooks.io/linux-insides/content/',
    },
  ],
  计算机网络: [
    {
      id: 'computer-networking-top-down',
      title: 'Computer Networking: A Top-Down Approach',
      authors: ['James F. Kurose', 'Keith W. Ross'],
      source: 'Pearson',
      cover_url: '',
      description: '从应用层向下讲解网络协议和互联网体系。',
      level: '入门',
      tags: ['计算机网络'],
      related_knowledge_points: ['应用层'],
      reason: '适合快速建立网络协议整体视图。',
      url: 'https://gaia.cs.umass.edu/kurose_ross/',
    },
    {
      id: 'tcp-ip-guide',
      title: 'The TCP/IP Guide',
      authors: ['Charles M. Kozierok'],
      source: 'tcpipguide.com',
      cover_url: '',
      description: '系统整理 TCP/IP 协议族、寻址、路由和传输机制。',
      level: '进阶',
      tags: ['TCP/IP'],
      related_knowledge_points: ['传输层'],
      reason: '适合查阅具体协议细节。',
      url: 'http://www.tcpipguide.com/',
    },
    {
      id: 'wireshark-labs',
      title: 'Wireshark Labs',
      authors: ['Kurose & Ross'],
      source: 'Wireshark Labs',
      cover_url: '',
      description: '通过抓包实验观察 HTTP、DNS、TCP 和 IP 的真实交互。',
      level: '实战',
      tags: ['抓包实验'],
      related_knowledge_points: ['网络层'],
      reason: '适合把协议字段和实际报文对应起来。',
      url: 'https://gaia.cs.umass.edu/kurose_ross/wireshark.php',
    },
    {
      id: 'rfc-editor',
      title: 'RFC Editor',
      authors: ['IETF'],
      source: 'RFC Editor',
      cover_url: '',
      description: '互联网协议标准文档入口。',
      level: '进阶',
      tags: ['协议标准'],
      related_knowledge_points: ['路由与拥塞控制'],
      reason: '适合查阅协议规范和标准定义。',
      url: 'https://www.rfc-editor.org/',
    },
  ],
}

function mergeCoursesWithFallback(courses: CourseSummary[]) {
  const courseMap = new Map<string, CourseSummary>()
  FALLBACK_COURSES.forEach((course) => {
    if (course.name.trim()) {
      courseMap.set(course.name, course)
    }
  })
  courses.forEach((course) => {
    if (!courseMap.has(course.name)) {
      courseMap.set(course.name, course)
    }
  })
  return Array.from(courseMap.values())
}

function canonicalFallbackCourseName(courseName: string | undefined) {
  const text = courseName || ''
  const dataStructures = '\u6570\u636e\u7ed3\u6784'
  const computerOrganization = '\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406'
  const operatingSystem = '\u64cd\u4f5c\u7cfb\u7edf'
  const computerNetwork = '\u8ba1\u7b97\u673a\u7f51\u7edc'

  if (text.includes('\u7f51\u7edc') || text.includes('TCP') || text.includes('HTTP')) {
    return computerNetwork
  }
  if (text.includes('\u64cd\u4f5c\u7cfb\u7edf')) {
    return operatingSystem
  }
  if (
    text.includes('\u7ec4\u6210') ||
    text.includes('\u4f53\u7cfb\u7ed3\u6784') ||
    text.includes('\u8ba1\u7b97\u673a\u7cfb\u7edf')
  ) {
    return computerOrganization
  }
  if (text.includes('\u6570\u636e\u7ed3\u6784') || text.includes('\u7b97\u6cd5')) {
    return dataStructures
  }
  return ''
}

function fallbackCourseForNotebookTitle(title: string | undefined | null) {
  const canonical = canonicalFallbackCourseName(title || '')
  return FALLBACK_COURSES.find((course) => course.name === canonical) || DEMO_COURSE
}

function richFallbackGraphForCourse(course: CourseSummary | undefined) {
  const targetCourse = course || DEMO_COURSE
  const canonical = canonicalFallbackCourseName(targetCourse.name)

  if (canonical === '\u6570\u636e\u7ed3\u6784') {
    return createFallbackGraph(
      targetCourse,
      [
        { id: 'complexity', label: '\u7b97\u6cd5\u590d\u6742\u5ea6', description: '\u7528\u65f6\u95f4\u548c\u7a7a\u95f4\u590d\u6742\u5ea6\u8bc4\u4f30\u7ed3\u6784\u9009\u578b\u548c\u7b97\u6cd5\u6548\u7387\u3002', importance: 'core' },
        { id: 'linear-list', label: '\u7ebf\u6027\u8868', description: '\u6bd4\u8f83\u987a\u5e8f\u5b58\u50a8\u548c\u94fe\u5f0f\u5b58\u50a8\u7684\u589e\u5220\u67e5\u6539\u4ee3\u4ef7\u3002', importance: 'core' },
        { id: 'stack-queue', label: '\u6808\u4e0e\u961f\u5217', description: '\u638c\u63e1 LIFO/FIFO \u6a21\u578b\u53ca\u8868\u8fbe\u5f0f\u3001\u9012\u5f52\u3001\u5c42\u6b21\u904d\u5386\u5e94\u7528\u3002', importance: 'important' },
        { id: 'string-array', label: '\u4e32\u4e0e\u6570\u7ec4', description: '\u7406\u89e3\u7d22\u5f15\u3001\u5b50\u4e32\u3001\u5339\u914d\u548c\u8fde\u7eed\u5b58\u50a8\u7684\u8bbe\u8ba1\u7ea6\u675f\u3002', importance: 'normal' },
        { id: 'tree', label: '\u6811\u4e0e\u4e8c\u53c9\u6811', description: '\u5efa\u7acb\u9012\u5f52\u7ed3\u6784\u3001\u904d\u5386\u5e8f\u5217\u548c\u6811\u578b\u5b58\u50a8\u76f4\u89c9\u3002', importance: 'core' },
        { id: 'graph', label: '\u56fe\u7ed3\u6784', description: '\u638c\u63e1\u90bb\u63a5\u8868\u3001\u90bb\u63a5\u77e9\u9635\u3001DFS/BFS \u548c\u8fde\u901a\u6027\u5206\u6790\u3002', importance: 'core' },
        { id: 'search', label: '\u67e5\u627e', description: '\u4ece\u987a\u5e8f\u67e5\u627e\u3001\u4e8c\u5206\u67e5\u627e\u8fc7\u6e21\u5230\u6811\u8868\u548c\u54c8\u5e0c\u67e5\u627e\u3002', importance: 'important' },
        { id: 'sorting', label: '\u6392\u5e8f', description: '\u6bd4\u8f83\u63d2\u5165\u3001\u5feb\u6392\u3001\u5f52\u5e76\u3001\u5806\u6392\u7684\u7a33\u5b9a\u6027\u548c\u590d\u6742\u5ea6\u3002', importance: 'important' },
        { id: 'hash-table', label: '\u54c8\u5e0c\u8868', description: '\u7406\u89e3\u54c8\u5e0c\u51fd\u6570\u3001\u51b2\u7a81\u5904\u7406\u548c\u5e73\u5747\u590d\u6742\u5ea6\u6761\u4ef6\u3002', importance: 'normal' },
        { id: 'heap-priority-queue', label: '\u5806\u4e0e\u4f18\u5148\u961f\u5217', description: '\u628a\u5b8c\u5168\u4e8c\u53c9\u6811\u548c\u4f18\u5148\u7ea7\u8c03\u5ea6\u3001TopK \u95ee\u9898\u8054\u7cfb\u8d77\u6765\u3002', importance: 'important' },
        { id: 'union-find', label: '\u5e76\u67e5\u96c6', description: '\u7528\u8def\u5f84\u538b\u7f29\u548c\u6309\u79e9\u5408\u5e76\u89e3\u51b3\u52a8\u6001\u8fde\u901a\u6027\u95ee\u9898\u3002', importance: 'normal' },
      ],
      [
        { source: 'complexity', target: 'linear-list', relation: 'prerequisite' },
        { source: 'linear-list', target: 'stack-queue', relation: 'prerequisite' },
        { source: 'linear-list', target: 'string-array', relation: 'related' },
        { source: 'stack-queue', target: 'tree', relation: 'prerequisite' },
        { source: 'stack-queue', target: 'graph', relation: 'prerequisite' },
        { source: 'complexity', target: 'search', relation: 'related' },
        { source: 'complexity', target: 'sorting', relation: 'related' },
        { source: 'search', target: 'hash-table', relation: 'advanced' },
        { source: 'tree', target: 'heap-priority-queue', relation: 'advanced' },
        { source: 'graph', target: 'union-find', relation: 'advanced' },
      ],
    )
  }

  if (canonical === '\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406') {
    return createFallbackGraph(
      targetCourse,
      [
        { id: 'data-representation', label: '\u6570\u636e\u8868\u793a', description: '\u7406\u89e3\u8fdb\u5236\u3001\u8865\u7801\u3001\u6d6e\u70b9\u6570\u548c\u4fe1\u606f\u7f16\u7801\u3002', importance: 'core' },
        { id: 'alu', label: '\u8fd0\u7b97\u5668\u4e0e ALU', description: '\u638c\u63e1\u7b97\u672f\u903b\u8f91\u8fd0\u7b97\u3001\u6807\u5fd7\u4f4d\u548c\u6570\u636e\u901a\u8def\u57fa\u7840\u3002', importance: 'core' },
        { id: 'memory-system', label: '\u5b58\u50a8\u7cfb\u7edf', description: '\u5206\u6790\u4e3b\u5b58\u3001\u8f85\u5b58\u3001\u5730\u5740\u7f16\u7801\u548c\u5c42\u6b21\u5b58\u50a8\u3002', importance: 'core' },
        { id: 'instruction-system', label: '\u6307\u4ee4\u7cfb\u7edf', description: '\u7406\u89e3\u6307\u4ee4\u683c\u5f0f\u3001\u5bfb\u5740\u65b9\u5f0f\u548c ISA \u4e0e\u786c\u4ef6\u7684\u63a5\u53e3\u3002', importance: 'core' },
        { id: 'cpu-datapath', label: 'CPU \u6570\u636e\u901a\u8def', description: '\u628a\u5bc4\u5b58\u5668\u3001ALU\u3001\u63a7\u5236\u4fe1\u53f7\u4e32\u8054\u4e3a\u6307\u4ee4\u6267\u884c\u8fc7\u7a0b\u3002', importance: 'important' },
        { id: 'controller', label: '\u63a7\u5236\u5668', description: '\u533a\u5206\u786c\u5e03\u7ebf\u63a7\u5236\u548c\u5fae\u7a0b\u5e8f\u63a7\u5236\u7684\u7ec4\u7ec7\u65b9\u5f0f\u3002', importance: 'important' },
        { id: 'bus', label: '\u603b\u7ebf', description: '\u7406\u89e3\u6570\u636e\u3001\u5730\u5740\u3001\u63a7\u5236\u603b\u7ebf\u53ca\u4ef2\u88c1\u4f20\u8f93\u673a\u5236\u3002', importance: 'normal' },
        { id: 'io-system', label: '\u8f93\u5165\u8f93\u51fa\u7cfb\u7edf', description: '\u638c\u63e1\u7a0b\u5e8f\u67e5\u8be2\u3001\u4e2d\u65ad\u3001DMA \u548c\u5916\u8bbe\u63a5\u53e3\u3002', importance: 'important' },
        { id: 'pipeline', label: '\u6d41\u6c34\u7ebf', description: '\u5206\u6790\u6307\u4ee4\u5e76\u884c\u3001\u5192\u9669\u3001\u505c\u987f\u548c\u541e\u5410\u7387\u63d0\u5347\u3002', importance: 'important' },
        { id: 'cache', label: 'Cache', description: '\u7406\u89e3\u6620\u5c04\u3001\u66ff\u6362\u3001\u5199\u7b56\u7565\u548c\u5c40\u90e8\u6027\u539f\u7406\u3002', importance: 'core' },
        { id: 'interrupt-exception', label: '\u4e2d\u65ad\u4e0e\u5f02\u5e38', description: '\u628a CPU \u6267\u884c\u3001I/O \u548c\u64cd\u4f5c\u7cfb\u7edf\u54cd\u5e94\u673a\u5236\u8fde\u63a5\u8d77\u6765\u3002', importance: 'normal' },
      ],
      [
        { source: 'data-representation', target: 'alu', relation: 'prerequisite' },
        { source: 'alu', target: 'cpu-datapath', relation: 'prerequisite' },
        { source: 'instruction-system', target: 'cpu-datapath', relation: 'prerequisite' },
        { source: 'controller', target: 'cpu-datapath', relation: 'related' },
        { source: 'memory-system', target: 'cache', relation: 'advanced' },
        { source: 'cpu-datapath', target: 'pipeline', relation: 'advanced' },
        { source: 'bus', target: 'io-system', relation: 'prerequisite' },
        { source: 'io-system', target: 'interrupt-exception', relation: 'related' },
        { source: 'cache', target: 'pipeline', relation: 'related' },
      ],
    )
  }

  if (canonical === '\u64cd\u4f5c\u7cfb\u7edf') {
    return createFallbackGraph(
      targetCourse,
      [
        { id: 'process-thread', label: '\u8fdb\u7a0b\u4e0e\u7ebf\u7a0b', description: '\u7406\u89e3\u8d44\u6e90\u5206\u914d\u5355\u4f4d\u548c\u6267\u884c\u5355\u4f4d\u7684\u5dee\u5f02\u3002', importance: 'core' },
        { id: 'cpu-scheduling', label: '\u5904\u7406\u5668\u8c03\u5ea6', description: '\u6bd4\u8f83 FCFS\u3001SJF\u3001RR\u3001\u4f18\u5148\u7ea7\u7b49\u8c03\u5ea6\u7b56\u7565\u3002', importance: 'important' },
        { id: 'sync-mutual-exclusion', label: '\u540c\u6b65\u4e0e\u4e92\u65a5', description: '\u638c\u63e1\u4fe1\u53f7\u91cf\u3001\u7ba1\u7a0b\u3001\u9501\u548c\u5178\u578b\u5e76\u53d1\u95ee\u9898\u3002', importance: 'core' },
        { id: 'deadlock', label: '\u6b7b\u9501', description: '\u5206\u6790\u5fc5\u8981\u6761\u4ef6\u3001\u9884\u9632\u3001\u907f\u514d\u3001\u68c0\u6d4b\u4e0e\u89e3\u9664\u3002', importance: 'important' },
        { id: 'memory-management', label: '\u5185\u5b58\u7ba1\u7406', description: '\u7406\u89e3\u5206\u533a\u3001\u5206\u9875\u3001\u5206\u6bb5\u548c\u5730\u5740\u53d8\u6362\u673a\u5236\u3002', importance: 'core' },
        { id: 'virtual-memory', label: '\u865a\u62df\u5185\u5b58', description: '\u638c\u63e1\u9875\u8868\u3001TLB\u3001\u7f3a\u9875\u4e2d\u65ad\u548c\u5c40\u90e8\u6027\u3002', importance: 'core' },
        { id: 'page-replacement', label: '\u9875\u9762\u7f6e\u6362', description: '\u6bd4\u8f83 FIFO\u3001LRU\u3001Clock \u7b49\u7b56\u7565\u7684\u9002\u7528\u573a\u666f\u3002', importance: 'important' },
        { id: 'file-system', label: '\u6587\u4ef6\u7cfb\u7edf', description: '\u7406\u89e3\u76ee\u5f55\u3001\u7d22\u5f15\u8282\u70b9\u3001\u7a7a\u95f2\u7a7a\u95f4\u548c\u6743\u9650\u3002', importance: 'important' },
        { id: 'io-management', label: 'I/O \u7ba1\u7406', description: '\u68b3\u7406\u7f13\u51b2\u3001\u7f13\u5b58\u3001\u8bbe\u5907\u9a71\u52a8\u548c\u78c1\u76d8\u8c03\u5ea6\u3002', importance: 'normal' },
        { id: 'system-call', label: '\u7cfb\u7edf\u8c03\u7528', description: '\u628a\u7528\u6237\u6001\u4e0e\u5185\u6838\u6001\u7684\u8fb9\u754c\u3001\u63a5\u53e3\u548c\u5b89\u5168\u8fde\u63a5\u8d77\u6765\u3002', importance: 'normal' },
      ],
      [
        { source: 'process-thread', target: 'cpu-scheduling', relation: 'related' },
        { source: 'process-thread', target: 'sync-mutual-exclusion', relation: 'prerequisite' },
        { source: 'sync-mutual-exclusion', target: 'deadlock', relation: 'advanced' },
        { source: 'memory-management', target: 'virtual-memory', relation: 'advanced' },
        { source: 'virtual-memory', target: 'page-replacement', relation: 'advanced' },
        { source: 'file-system', target: 'io-management', relation: 'related' },
        { source: 'system-call', target: 'file-system', relation: 'related' },
        { source: 'system-call', target: 'io-management', relation: 'related' },
      ],
    )
  }

  if (canonical === '\u8ba1\u7b97\u673a\u7f51\u7edc') {
    return createFallbackGraph(
      targetCourse,
      [
        { id: 'tcp-ip-model', label: 'TCP/IP \u4f53\u7cfb', description: '\u628a\u5206\u5c42\u6a21\u578b\u4e0e\u7aef\u5230\u7aef\u901a\u4fe1\u8fc7\u7a0b\u5bf9\u9f50\u3002', importance: 'core' },
        { id: 'physical-layer', label: '\u7269\u7406\u5c42', description: '\u7406\u89e3\u4fe1\u9053\u3001\u7f16\u7801\u3001\u4f20\u8f93\u4ecb\u8d28\u548c\u5e26\u5bbd\u7ea6\u675f\u3002', importance: 'normal' },
        { id: 'data-link-layer', label: '\u6570\u636e\u94fe\u8def\u5c42', description: '\u638c\u63e1\u5e27\u3001MAC\u3001\u5dee\u9519\u63a7\u5236\u548c\u4ee5\u592a\u7f51\u5de5\u4f5c\u673a\u5236\u3002', importance: 'important' },
        { id: 'network-layer', label: '\u7f51\u7edc\u5c42', description: '\u7406\u89e3\u8de8\u7f51\u6bb5\u8f6c\u53d1\u3001\u5bfb\u5740\u548c\u8def\u7531\u9009\u62e9\u3002', importance: 'core' },
        { id: 'ip-protocol', label: 'IP \u534f\u8bae', description: '\u5b66\u4e60 IP \u5730\u5740\u3001\u5b50\u7f51\u5212\u5206\u3001\u5206\u7247\u548c ICMP\u3002', importance: 'core' },
        { id: 'routing-algorithm', label: '\u8def\u7531\u7b97\u6cd5', description: '\u6bd4\u8f83\u8ddd\u79bb\u5411\u91cf\u3001\u94fe\u8def\u72b6\u6001\u548c\u81ea\u6cbb\u7cfb\u7edf\u8def\u7531\u3002', importance: 'important' },
        { id: 'transport-layer', label: '\u4f20\u8f93\u5c42', description: '\u7406\u89e3\u7aef\u53e3\u3001\u590d\u7528\u5206\u7528\u3001\u53ef\u9760\u4f20\u8f93\u548c\u6d41\u91cf\u63a7\u5236\u3002', importance: 'core' },
        { id: 'tcp', label: 'TCP', description: '\u638c\u63e1\u4e09\u6b21\u63e1\u624b\u3001\u91cd\u4f20\u3001\u6ed1\u52a8\u7a97\u53e3\u548c\u8fde\u63a5\u91ca\u653e\u3002', importance: 'core' },
        { id: 'udp', label: 'UDP', description: '\u7406\u89e3\u65e0\u8fde\u63a5\u4f20\u8f93\u7684\u4f4e\u5ef6\u8fdf\u7279\u70b9\u548c\u9002\u7528\u573a\u666f\u3002', importance: 'normal' },
        { id: 'congestion-control', label: '\u62e5\u585e\u63a7\u5236', description: '\u7406\u89e3\u6162\u542f\u52a8\u3001\u62e5\u585e\u907f\u514d\u3001\u5feb\u91cd\u4f20\u548c\u5feb\u6062\u590d\u3002', importance: 'important' },
        { id: 'application-layer', label: '\u5e94\u7528\u5c42', description: '\u7406\u89e3\u5ba2\u6237\u7aef/\u670d\u52a1\u5668\u6a21\u5f0f\u548c\u5e38\u89c1\u5e94\u7528\u534f\u8bae\u3002', importance: 'core' },
        { id: 'dns', label: 'DNS', description: '\u638c\u63e1\u57df\u540d\u89e3\u6790\u3001\u9012\u5f52/\u8fed\u4ee3\u67e5\u8be2\u548c\u7f13\u5b58\u673a\u5236\u3002', importance: 'important' },
        { id: 'http-https', label: 'HTTP/HTTPS', description: '\u7406\u89e3\u62a5\u6587\u3001\u72b6\u6001\u7801\u3001\u7f13\u5b58\u3001TLS \u548c Web \u5b89\u5168\u57fa\u7840\u3002', importance: 'important' },
      ],
      [
        { source: 'tcp-ip-model', target: 'physical-layer', relation: 'prerequisite' },
        { source: 'physical-layer', target: 'data-link-layer', relation: 'prerequisite' },
        { source: 'data-link-layer', target: 'network-layer', relation: 'prerequisite' },
        { source: 'network-layer', target: 'ip-protocol', relation: 'related' },
        { source: 'network-layer', target: 'routing-algorithm', relation: 'advanced' },
        { source: 'network-layer', target: 'transport-layer', relation: 'prerequisite' },
        { source: 'transport-layer', target: 'tcp', relation: 'advanced' },
        { source: 'transport-layer', target: 'udp', relation: 'advanced' },
        { source: 'tcp', target: 'congestion-control', relation: 'advanced' },
        { source: 'transport-layer', target: 'application-layer', relation: 'prerequisite' },
        { source: 'application-layer', target: 'dns', relation: 'related' },
        { source: 'application-layer', target: 'http-https', relation: 'related' },
      ],
    )
  }

  return null
}

function fallbackGraphForCourse(course: CourseSummary | undefined) {
  return richFallbackGraphForCourse(course) || FALLBACK_GRAPHS_BY_COURSE[course?.name || DEMO_COURSE.name] || DEMO_GRAPH
}

const graphLegendItems: Array<{ label: string; className: string }> = [
  { label: '核心', className: 'is-core' },
  { label: '重点', className: 'is-important' },
  { label: '普通', className: 'is-normal' },
]

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function pickString(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
  }
  return ''
}

function containsChinese(value: string) {
  return /[\u3400-\u9fff]/u.test(value)
}

const CHINESE_NODE_LABEL_REPLACEMENTS: Record<string, string> = {
  CPU: '中央处理器',
  CACHE: '高速缓存',
  TCP: '传输控制协议',
  UDP: '用户数据报协议',
  DNS: '域名系统',
  HTTP: '超文本传输协议',
  HTTPS: '安全超文本传输协议',
  'HTTP/HTTPS': '网页传输协议',
  IP: '网际协议',
  IP协议: '网际协议',
  'I/O管理': '输入输出管理',
  IO管理: '输入输出管理',
  'I/O系统': '输入输出系统',
  IO系统: '输入输出系统',
  'OSI/TCP-IP模型': '网络分层模型',
  OSITCPIP模型: '网络分层模型',
}

function chineseOnlyNodeLabel(value: string) {
  const raw = value.trim()
  const normalized = raw.toLocaleUpperCase().replace(/\s+/g, '')
  const replacement = CHINESE_NODE_LABEL_REPLACEMENTS[normalized]
  if (replacement) {
    return replacement
  }
  const chineseLabel = Array.from(raw)
    .filter((character) => /[\u3400-\u9fff]/u.test(character))
    .join('')
  if (chineseLabel) {
    return chineseLabel.slice(0, 24)
  }
  return Object.entries(CHINESE_NODE_LABEL_REPLACEMENTS).find(([key]) =>
    normalized.includes(key),
  )?.[1] || ''
}

function normalizedGraphLabel(value: string) {
  const chineseLabel = chineseOnlyNodeLabel(value)
  if (chineseLabel) {
    return chineseLabel.toLocaleLowerCase()
  }
  return Array.from(value.toLocaleLowerCase())
    .filter((character) => /[\p{L}\p{N}]/u.test(character))
    .join('')
}

function normalizeImportance(value: unknown, difficulty?: unknown): GraphImportance {
  const raw = pickString(value).toLowerCase()
  if (raw === 'core') {
    return 'core'
  }
  if (raw === 'important' || raw === 'focus') {
    return 'important'
  }
  const difficultyText = pickString(difficulty).toLowerCase()
  if (difficultyText === 'hard' || difficultyText === 'comprehensive') {
    return 'core'
  }
  if (difficultyText === 'medium') {
    return 'important'
  }
  return 'normal'
}

function normalizeMastery(value: unknown): GraphMastery {
  const raw = pickString(value).toLowerCase()
  if (raw === 'weak' || raw === 'medium' || raw === 'mastered') {
    return raw
  }
  return 'unknown'
}

function normalizePrerequisites(value: unknown) {
  if (!Array.isArray(value)) {
    return []
  }
  return value
    .map((item) => {
      if (typeof item === 'string') {
        return item
      }
      if (item && typeof item === 'object') {
        return pickString((item as { id?: unknown }).id, (item as { name?: unknown }).name)
      }
      return ''
    })
    .filter(Boolean)
}

function getGraphLayoutShape(nodeCount: number) {
  const columns = nodeCount <= 8 ? 2 : nodeCount <= 14 ? 3 : 4
  const horizontalGap = columns === 2 ? 260 : columns === 3 ? 220 : 190
  const verticalGap = columns === 2 ? 172 : columns === 3 ? 156 : 146

  return {
    columns,
    horizontalGap,
    verticalGap,
    originX: columns === 2 ? 150 : 132,
    originY: 116,
  }
}

function getGraphLayoutTarget(nodeCount: number) {
  const layout = getGraphLayoutShape(nodeCount)
  const rows = Math.max(1, Math.ceil(nodeCount / layout.columns))
  const visibleColumns = Math.max(1, Math.min(nodeCount, layout.columns))

  return {
    x: layout.originX + ((visibleColumns - 1) * layout.horizontalGap) / 2,
    y: layout.originY + ((rows - 1) * layout.verticalGap) / 2 + 24,
  }
}

function layoutGraphNodes(
  nodes: Array<Omit<GraphNode, 'x' | 'y'> & Partial<Pick<GraphNode, 'x' | 'y'>>>,
): GraphNode[] {
  const sorted = [...nodes].sort((left, right) => left.order - right.order)
  const layout = getGraphLayoutShape(sorted.length)

  return sorted.map((node, index) => {
    const column = index % layout.columns
    const row = Math.floor(index / layout.columns)
    return {
      ...node,
      x:
        typeof node.x === 'number' && Number.isFinite(node.x)
          ? node.x
          : layout.originX + column * layout.horizontalGap + (row % 2) * 18,
      y:
        typeof node.y === 'number' && Number.isFinite(node.y)
          ? node.y
          : layout.originY + row * layout.verticalGap + (column % 2) * 38,
    }
  })
}

function datasetFromResponse(response: KnowledgeGraphResponse): GraphDataset {
  if (Array.isArray(response)) {
    return datasetFromNodeList(response, 'database')
  }

  const rawNodes = Array.isArray(response.nodes) ? response.nodes : []
  const nodes = layoutGraphNodes(
    rawNodes.map((item, index) => ({
      id: pickString(item.id) || `node-${index + 1}`,
      label: pickString(item.label, item.name, item.title) || `知识点 ${index + 1}`,
      description: pickString(item.description) || '暂无简介',
      chapter: pickString(item.chapter),
      importance: normalizeImportance(item.importance, item.difficulty),
      mastery: normalizeMastery(item.mastery),
      order: typeof item.order === 'number' ? item.order : index + 1,
      x: typeof item.x === 'number' ? item.x : undefined,
      y: typeof item.y === 'number' ? item.y : undefined,
    })),
  )
  const nodeIds = new Set(nodes.map((node) => node.id))
  const edges = normalizeEdges(response.edges, nodeIds)

  return {
    nodes,
    edges,
    source:
      response.source === 'agent'
        ? 'agent'
        : response.source === 'fallback'
          ? 'fallback'
          : response.source === 'local'
            ? 'local'
            : 'database',
  }
}

function datasetFromNodeList(
  graphItems: KnowledgeGraphNode[],
  source: GraphDataset['source'],
): GraphDataset {
  const nodes = layoutGraphNodes(
    graphItems.map((item, index) => ({
      id: pickString(item.id) || `node-${index + 1}`,
      label: pickString(item.label, item.name, item.title) || `知识点 ${index + 1}`,
      description: pickString(item.description) || '暂无简介',
      chapter: pickString(item.chapter),
      importance: normalizeImportance(item.importance, item.difficulty),
      mastery: normalizeMastery(item.mastery),
      order: typeof item.order === 'number' ? item.order : index + 1,
      x: typeof item.x === 'number' ? item.x : undefined,
      y: typeof item.y === 'number' ? item.y : undefined,
    })),
  )
  const nodeIds = new Set(nodes.map((node) => node.id))
  const edges = graphItems.flatMap((item, targetIndex) => {
    const target = nodes[targetIndex]
    if (!target) {
      return []
    }
    return normalizePrerequisites(item.prerequisites)
      .filter((sourceId) => nodeIds.has(sourceId))
      .map((sourceId, index) => ({
        id: `${sourceId}-${target.id}-${index}`,
        source: sourceId,
        target: target.id,
        relation: 'prerequisite',
        description: '',
      }))
  })

  return { nodes, edges, source }
}

function normalizeEdges(rawEdges: KnowledgeGraphEdge[] | undefined, nodeIds: Set<string>) {
  if (!Array.isArray(rawEdges)) {
    return []
  }
  return rawEdges
    .map((edge, index) => ({
      id: pickString(edge.id) || `${edge.source}-${edge.target}-${index}`,
      source: pickString(edge.source),
      target: pickString(edge.target),
      relation: pickString(edge.relation) || 'related',
      description: pickString(edge.description, edge.reason),
    }))
    .filter((edge) => edge.source && edge.target && edge.source !== edge.target)
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
}

function graphPayloadForUpdate(nodes: GraphNode[], edges: GraphEdge[]) {
  return {
    nodes: nodes.slice(0, 16).map((node) => ({
      id: node.id,
      label: node.label,
      description: node.description,
      importance: node.importance,
      mastery: node.mastery,
      chapter: node.chapter,
      order: node.order,
      x: node.x,
      y: node.y,
    })),
    edges: edges.slice(0, 28).map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      relation: edge.relation,
      description: edge.description,
    })),
  }
}

function datasetFromUpdateResponse(
  response: KnowledgeGraphResponse,
  currentNodes: GraphNode[],
): GraphDataset {
  if (Array.isArray(response)) {
    return datasetFromNodeList(response, 'database')
  }

  const rawNodes = Array.isArray(response.nodes) ? response.nodes : []
  const currentNodeIds = new Set(currentNodes.map((node) => node.id))
  const currentLabelOwners = new Map(
    currentNodes.map((node) => [normalizedGraphLabel(node.label), node.id]),
  )
  const nodeIdAliases = new Map<string, string>()
  const acceptedLabelOwners = new Map(currentLabelOwners)
  const candidateNodes = rawNodes.map((item, index) => {
    const id = pickString(item.id) || `node-${index + 1}`
    const label = pickString(item.label, item.name, item.title) || `知识点 ${index + 1}`
    const rawDescription = pickString(item.description)
    const description =
      currentNodeIds.has(id) || containsChinese(rawDescription)
        ? rawDescription || '暂无简介'
        : `梳理${label}的核心概念、适用场景和相关知识。`
    return {
      id,
      label,
      description,
      chapter: pickString(item.chapter),
      importance: normalizeImportance(item.importance, item.difficulty),
      mastery: normalizeMastery(item.mastery),
      order: typeof item.order === 'number' ? item.order : index + 1,
      x: typeof item.x === 'number' ? item.x : undefined,
      y: typeof item.y === 'number' ? item.y : undefined,
    }
  })
  const uniqueNodes = candidateNodes.filter((node) => {
    if (currentNodeIds.has(node.id)) {
      return true
    }
    if (!containsChinese(node.label)) {
      return false
    }
    const labelKey = normalizedGraphLabel(node.label)
    const existingOwnerId = acceptedLabelOwners.get(labelKey)
    if (existingOwnerId) {
      nodeIdAliases.set(node.id, existingOwnerId)
      return false
    }
    acceptedLabelOwners.set(labelKey, node.id)
    return true
  })
  const nodes = layoutGraphNodes(uniqueNodes)
  const nodeIds = new Set([...currentNodes.map((node) => node.id), ...nodes.map((node) => node.id)])
  const remappedEdges = response.edges?.map((edge) => ({
    ...edge,
    source: nodeIdAliases.get(pickString(edge.source)) || edge.source,
    target: nodeIdAliases.get(pickString(edge.target)) || edge.target,
  }))
  const edges = normalizeEdges(remappedEdges, nodeIds)

  return {
    nodes,
    edges,
    source:
      response.source === 'agent'
        ? 'agent'
        : response.source === 'fallback'
          ? 'fallback'
          : response.source === 'local'
            ? 'local'
            : 'database',
  }
}

function edgeMergeKey(edge: Pick<GraphEdge, 'source' | 'target' | 'relation'>) {
  return `${edge.source}->${edge.target}:${edge.relation || 'related'}`
}

function mergeGraphPreserveLayout(
  currentNodes: GraphNode[],
  currentEdges: GraphEdge[],
  incoming: GraphDataset,
  selectedNodeId: string,
) {
  const currentById = new Map(currentNodes.map((node) => [node.id, node]))
  const incomingById = new Map(incoming.nodes.map((node) => [node.id, node]))
  const labelOwnerIds = new Map(
    currentNodes.map((node) => [normalizedGraphLabel(node.label), node.id]),
  )
  const nodeIdAliases = new Map<string, string>()
  const anchor =
    currentById.get(selectedNodeId) ||
    currentNodes.find((node) => node.importance === 'core') ||
    currentNodes[0] ||
    incoming.nodes[0]
  const addedNodeIds: string[] = []
  const addedEdgeIds: string[] = []
  const nodeVelocitySeeds = new Map<string, NodeVelocity>()

  const mergedExistingNodes = currentNodes.map((node) => {
    const next = incomingById.get(node.id)
    if (!next) {
      return node
    }
    return {
      ...node,
      label: next.label || node.label,
      description: next.description || node.description,
      chapter: next.chapter || node.chapter,
      importance: next.importance || node.importance,
      mastery: next.mastery || node.mastery,
      order: next.order || node.order,
    }
  })

  const newNodes = incoming.nodes
    .filter((node) => !currentById.has(node.id))
    .filter((node) => {
      const labelKey = normalizedGraphLabel(node.label)
      const existingOwnerId = labelOwnerIds.get(labelKey)
      if (existingOwnerId) {
        nodeIdAliases.set(node.id, existingOwnerId)
        return false
      }
      labelOwnerIds.set(labelKey, node.id)
      return true
    })
    .map((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(1, incoming.nodes.length) + Math.PI / 7
      const radius = 86 + (index % 4) * 18
      const seededVelocity = {
        vx: Math.cos(angle) * 1.8,
        vy: Math.sin(angle) * 1.8,
      }
      addedNodeIds.push(node.id)
      nodeVelocitySeeds.set(node.id, seededVelocity)
      return {
        ...node,
        x: (anchor?.x ?? 180) + Math.cos(angle) * radius,
        y: (anchor?.y ?? 140) + Math.sin(angle) * radius,
      }
    })

  const nodes = [...mergedExistingNodes, ...newNodes]
  const validNodeIds = new Set(nodes.map((node) => node.id))
  const edgeMap = new Map<string, GraphEdge>()

  currentEdges.forEach((edge) => {
    if (validNodeIds.has(edge.source) && validNodeIds.has(edge.target)) {
      edgeMap.set(edgeMergeKey(edge), edge)
    }
  })

  incoming.edges.forEach((edge, index) => {
    const source = nodeIdAliases.get(edge.source) || edge.source
    const target = nodeIdAliases.get(edge.target) || edge.target
    if (!validNodeIds.has(source) || !validNodeIds.has(target) || source === target) {
      return
    }
    const remappedEdge = { ...edge, source, target }
    const key = edgeMergeKey(remappedEdge)
    if (edgeMap.has(key)) {
      return
    }
    const edgeId = edge.id || `${edge.source}-${edge.target}-${index}`
    addedEdgeIds.push(edgeId)
    edgeMap.set(key, {
      ...remappedEdge,
      id: edgeId,
      relation: edge.relation || 'related',
    })
  })

  return {
    nodes,
    edges: Array.from(edgeMap.values()),
    addedNodeIds,
    addedEdgeIds,
    nodeVelocitySeeds,
  }
}

function localExpansionDataset(
  course: CourseSummary | undefined,
  node: GraphNode | undefined,
  question: string,
  existingNodes: GraphNode[],
): GraphDataset {
  const topicText = `${node?.id || ''} ${node?.label || ''} ${question}`.toLowerCase()
  const topicLabel = node?.label || course?.name || '\u5f53\u524d\u77e5\u8bc6\u70b9'
  const baseId = (node?.id || 'topic').replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 36) || 'topic'
  const existingIds = new Set(existingNodes.map((item) => item.id))
  const existingLabelKeys = new Set(existingNodes.map((item) => normalizedGraphLabel(item.label)))

  const templates: Array<{ id: string; label: string; description: string; importance: GraphImportance }> =
    topicText.includes('tcp')
      ? [
          { id: 'reliable-transport', label: 'TCP 可靠传输', description: '理解确认、重传和有序字节流交付机制。', importance: 'important' },
          { id: 'congestion-window', label: '拥塞窗口', description: '理解慢启动、拥塞避免和快速恢复过程。', importance: 'important' },
          { id: 'tcp-handshake', label: 'TCP 三次握手', description: '理解连接建立、序列号和状态转换。', importance: 'normal' },
        ]
      : topicText.includes('dns')
        ? [
            { id: 'recursive-resolution', label: 'DNS 递归解析', description: '理解解析器、根服务器、顶级域和权威服务器的查询链路。', importance: 'important' },
            { id: 'dns-records', label: 'DNS 资源记录', description: '掌握域名解析使用的常见资源记录。', importance: 'normal' },
            { id: 'dns-cache', label: 'DNS 缓存', description: '理解生存时间、缓存命中和过期记录排查。', importance: 'normal' },
          ]
        : topicText.includes('virtual') || topicText.includes('memory') || topicText.includes('\u865a\u62df')
          ? [
              { id: 'page-fault', label: '缺页异常', description: '理解缺页触发、操作系统处理和指令重启流程。', importance: 'important' },
              { id: 'tlb', label: '地址转换后备缓冲器（TLB）', description: '理解地址转换缓存及其对访存延迟的影响。', importance: 'normal' },
              { id: 'working-set', label: '工作集', description: '从局部性角度理解活跃页面和抖动风险。', importance: 'normal' },
            ]
          : topicText.includes('deadlock') || topicText.includes('\u6b7b\u9501')
            ? [
                { id: 'banker-algorithm', label: '银行家算法', description: '通过安全状态检查实现死锁避免。', importance: 'important' },
                { id: 'wait-for-graph', label: '资源等待图', description: '通过进程和资源之间的环路检测死锁。', importance: 'normal' },
                { id: 'deadlock-prevention', label: '死锁预防', description: '通过破坏死锁必要条件来预防死锁。', importance: 'normal' },
              ]
            : topicText.includes('tree') || topicText.includes('\u6811')
              ? [
                  { id: 'tree-traversal', label: '树的遍历', description: '掌握前序、中序、后序和层序遍历。', importance: 'important' },
                  { id: 'binary-search-tree', label: '二叉搜索树', description: '理解有序树操作和结构退化风险。', importance: 'important' },
                  { id: 'balanced-tree', label: '平衡树', description: '理解 AVL 树和红黑树保障查找效率的动机。', importance: 'normal' },
                ]
              : topicText.includes('sort') || topicText.includes('\u6392\u5e8f')
                ? [
                    { id: 'quick-sort', label: '快速排序', description: '理解分区、基准选择和平均时间复杂度。', importance: 'important' },
                    { id: 'merge-sort', label: '归并排序', description: '理解分治排序和稳定合并过程。', importance: 'important' },
                    { id: 'sort-stability', label: '排序稳定性', description: '理解相同关键字记录保持相对顺序的意义。', importance: 'normal' },
                  ]
                : [
                    { id: 'concept-boundary', label: '概念边界', description: `梳理${topicLabel}的适用范围、先修知识和常见误区。`, importance: 'normal' },
                    { id: 'practice-case', label: '练习案例', description: `通过小型应用场景检验对${topicLabel}的理解。`, importance: 'normal' },
                  ]

  const nodes = templates
    .map((item, index) => {
      const label = chineseOnlyNodeLabel(item.label)
      return {
        ...item,
        label,
        id: existingIds.has(item.id) ? `${baseId}-${item.id}` : item.id,
        chapter: '',
        mastery: 'unknown' as GraphMastery,
        order: existingNodes.length + index + 1,
        x: 0,
        y: 0,
      }
    })
    .filter((item) => item.label)
    .filter((item) => !existingIds.has(item.id))
    .filter((item) => !existingLabelKeys.has(normalizedGraphLabel(item.label)))
    .slice(0, 2)

  const edges = nodes.map((item, index) => ({
    id: `${baseId}-${item.id}-extension-${index}`,
    source: node?.id || existingNodes[0]?.id || item.id,
    target: item.id,
    relation: index === 0 ? 'advanced' : 'related',
    description: `${item.label}是${topicLabel}的进一步拓展。`,
  }))

  return {
    nodes,
    edges,
    source: 'local',
  }
}

function getNodeRadius(node: GraphNode) {
  if (node.importance === 'core') {
    return 46
  }
  if (node.importance === 'important') {
    return 39
  }
  return 31
}

function labelLines(label: string) {
  const chars = Array.from(label)
  if (chars.length <= 6) {
    return [label]
  }
  const first = chars.slice(0, 6).join('')
  const second = chars.slice(6, 12).join('') + (chars.length > 12 ? '…' : '')
  return [first, second]
}

function relationLabel(relation: string) {
  if (relation === 'prerequisite') {
    return '前置关系'
  }
  if (relation === 'advanced') {
    return '进阶关系'
  }
  if (relation === 'related') {
    return '相关知识'
  }
  return relation || '相关知识'
}

function importanceLabel(importance: GraphImportance) {
  if (importance === 'core') {
    return '核心'
  }
  if (importance === 'important') {
    return '重点'
  }
  return '普通'
}

function masteryLabel(mastery: GraphMastery) {
  if (mastery === 'weak') {
    return '薄弱'
  }
  if (mastery === 'medium') {
    return '一般'
  }
  if (mastery === 'mastered') {
    return '已掌握'
  }
  return '未知'
}

function edgeDescription(edge: GraphEdge, source: GraphNode, target: GraphNode) {
  if (edge.description) {
    return edge.description
  }
  if (edge.relation === 'prerequisite') {
    return `掌握 ${source.label} 有助于理解 ${target.label}。`
  }
  if (edge.relation === 'advanced') {
    return `${target.label} 是 ${source.label} 的进一步拓展。`
  }
  return `${source.label} 与 ${target.label} 在学习路径中相互关联。`
}

function topicTextForRecommendation(course: CourseSummary | undefined, node: GraphNode | undefined) {
  return `${canonicalFallbackCourseName(course?.name) || course?.name || ''} ${node?.id || ''} ${
    node?.label || ''
  }`.toLowerCase()
}

function recommendationItem(
  id: string,
  title: string,
  source: string,
  url: string,
  description: string,
  topic: string,
  level = '\u8fdb\u9636',
): ResourceRecommendation {
  return {
    id,
    title,
    authors: [],
    source,
    cover_url: '',
    description,
    level,
    tags: [topic],
    related_knowledge_points: [topic],
    reason: `Recommended for ${topic}: ${description}`,
    url,
  }
}

function profileResourceToRecommendation(
  item: UserProfileLearningResource,
  index: number,
  topic: string,
): ResourceRecommendation {
  return {
    id: `profile-resource-${index}-${item.title}`,
    title: item.title,
    authors: [],
    source: item.language === 'zh' ? '用户画像推荐' : 'Profile recommendation',
    cover_url: '',
    description: item.reason,
    level: item.language === 'zh' ? '中文' : '英文',
    tags: [topic],
    related_knowledge_points: [topic],
    reason: item.reason,
    url: item.url,
  }
}

function topicRecommendationItems(course: CourseSummary | undefined, node: GraphNode | undefined) {
  const topicText = topicTextForRecommendation(course, node)
  const topic = node?.label || course?.name || '\u5f53\u524d\u8bfe\u7a0b'

  if (topicText.includes('tcp')) {
    return [
      recommendationItem('topic-cs144', 'Stanford CS144: Introduction to Computer Networking', 'Stanford CS144', 'https://cs144.github.io/', 'TCP, reliable transport, and network protocol implementation.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-tcp-ip-guide', 'The TCP/IP Guide', 'tcpipguide.com', 'http://www.tcpipguide.com/', 'Protocol-level reference for TCP/IP addressing, routing, and transport.', topic),
      recommendationItem('topic-wireshark-tcp', 'Wireshark TCP Lab', 'Kurose & Ross', 'https://gaia.cs.umass.edu/kurose_ross/wireshark.php', 'Packet-trace labs for observing TCP behavior directly.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-rfc-9293', 'RFC 9293: Transmission Control Protocol', 'IETF RFC Editor', 'https://www.rfc-editor.org/rfc/rfc9293', 'Current public standard for TCP.', topic),
    ]
  }

  if (topicText.includes('dns')) {
    return [
      recommendationItem('topic-mdn-dns', 'MDN: How DNS works', 'MDN Web Docs', 'https://developer.mozilla.org/en-US/docs/Learn/Common_questions/Web_mechanics/What_is_a_domain_name', 'Readable introduction to domain names and DNS resolution.', topic, '\u5165\u95e8'),
      recommendationItem('topic-cloudflare-dns', 'Cloudflare Learning Center: What is DNS?', 'Cloudflare', 'https://www.cloudflare.com/learning/dns/what-is-dns/', 'Clear DNS resolver, nameserver, and record explanations.', topic, '\u5165\u95e8'),
      recommendationItem('topic-wireshark-dns', 'Wireshark DNS Lab', 'Kurose & Ross', 'https://gaia.cs.umass.edu/kurose_ross/wireshark.php', 'Hands-on DNS packet analysis.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-rfc-1034', 'RFC 1034: Domain Names - Concepts and Facilities', 'IETF RFC Editor', 'https://www.rfc-editor.org/rfc/rfc1034', 'Original public DNS architecture specification.', topic),
    ]
  }

  if (topicText.includes('network-layer') || topicText.includes('\u7f51\u7edc\u5c42') || topicText.includes('ip-protocol')) {
    return [
      recommendationItem('topic-kurose-network-layer', 'Computer Networking: A Top-Down Approach', 'Kurose & Ross', 'https://gaia.cs.umass.edu/kurose_ross/', 'Network-layer forwarding, routing, and IP overview.', topic),
      recommendationItem('topic-tcpip-ip', 'The TCP/IP Guide: Internet Protocol', 'tcpipguide.com', 'http://www.tcpipguide.com/free/t_InternetProtocolIPAddressing.htm', 'IP addressing and network-layer reference.', topic),
      recommendationItem('topic-rfc-editor-ip', 'RFC Editor', 'IETF RFC Editor', 'https://www.rfc-editor.org/', 'Public protocol standards for IP and routing topics.', topic),
    ]
  }

  if (topicText.includes('virtual') || topicText.includes('memory') || topicText.includes('\u865a\u62df\u5185\u5b58')) {
    return [
      recommendationItem('topic-ostep-vm', 'Operating Systems: Three Easy Pieces', 'OSTEP', 'https://pages.cs.wisc.edu/~remzi/OSTEP/', 'Virtual memory, address spaces, paging, and replacement chapters.', topic, '\u5165\u95e8'),
      recommendationItem('topic-mit-6s081-memory', 'MIT 6.S081 Operating System Engineering', 'MIT PDOS', 'https://pdos.csail.mit.edu/6.S081/', 'xv6 labs and notes for virtual memory implementation.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-xv6-riscv', 'xv6-riscv', 'MIT PDOS', 'https://github.com/mit-pdos/xv6-riscv', 'Teaching OS source code for memory management study.', topic, '\u5b9e\u6218'),
    ]
  }

  if (topicText.includes('deadlock') || topicText.includes('\u6b7b\u9501')) {
    return [
      recommendationItem('topic-ostep-deadlock', 'Operating Systems: Three Easy Pieces', 'OSTEP', 'https://pages.cs.wisc.edu/~remzi/OSTEP/', 'Deadlock conditions, prevention, avoidance, and detection.', topic, '\u5165\u95e8'),
      recommendationItem('topic-cs162-deadlock', 'Berkeley CS162 Operating Systems and Systems Programming', 'Berkeley CS162', 'https://cs162.org/', 'University OS material covering synchronization and deadlocks.', topic),
      recommendationItem('topic-geeks-deadlock', 'GeeksforGeeks: Deadlock in Operating System', 'GeeksforGeeks', 'https://www.geeksforgeeks.org/operating-systems/introduction-of-deadlock-in-operating-system/', 'Quick review of deadlock models and examples.', topic, '\u5165\u95e8'),
    ]
  }

  if (topicText.includes('tree') || topicText.includes('\u6811')) {
    return [
      recommendationItem('topic-opendsa-tree', 'OpenDSA: Binary Trees', 'OpenDSA', 'https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/BinaryTree.html', 'Interactive textbook chapter for tree and binary tree concepts.', topic),
      recommendationItem('topic-visualgo-bst', 'VisuAlgo: Binary Search Tree', 'VisuAlgo', 'https://visualgo.net/en/bst', 'Interactive BST operations and traversal visualization.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-open-data-structures-tree', 'Open Data Structures', 'opendatastructures.org', 'https://opendatastructures.org/', 'Open textbook chapters for binary trees and balanced search trees.', topic),
    ]
  }

  if (topicText.includes('sort') || topicText.includes('\u6392\u5e8f')) {
    return [
      recommendationItem('topic-visualgo-sorting', 'VisuAlgo: Sorting', 'VisuAlgo', 'https://visualgo.net/en/sorting', 'Interactive sorting algorithm visualization.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-cp-sorting', 'CP-Algorithms: Sorting and Searching', 'CP-Algorithms', 'https://cp-algorithms.com/', 'Implementation-oriented algorithm notes.', topic, '\u5b9e\u6218'),
      recommendationItem('topic-opendsa-sorting', 'OpenDSA: Sorting', 'OpenDSA', 'https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/Sorting.html', 'Textbook-style sorting concepts and exercises.', topic),
    ]
  }

  return []
}

function recommendationFallback(course: CourseSummary | undefined, node: GraphNode | undefined) {
  const courseName = course?.name || '\u5f53\u524d\u8bfe\u7a0b'
  const lookupName = canonicalFallbackCourseName(courseName)
  const knowledgeName = node?.label || courseName
  const topicItems = topicRecommendationItems(course, node)
  const templates =
    COURSE_RECOMMENDATIONS_BY_NAME[courseName] ||
    (lookupName ? COURSE_RECOMMENDATIONS_BY_NAME[lookupName] : undefined) ||
    LOCAL_RECOMMENDATIONS

  const seen = new Set(topicItems.map((item) => item.url || item.title))
  const courseItems = templates.filter((item) => {
    const key = item.url || item.title
    if (seen.has(key)) {
      return false
    }
    seen.add(key)
    return true
  })

  return [...topicItems, ...courseItems].slice(0, 7).map((item) => ({
    ...item,
    id: `${item.id}-${node?.id || course?.id || 'course'}`,
    tags: Array.from(new Set([courseName, knowledgeName, ...item.tags])),
    related_knowledge_points: Array.from(
      new Set([knowledgeName, ...item.related_knowledge_points]),
    ),
  }))
}

function displayResourceTitle(title: string, node: GraphNode | undefined) {
  const topic = node?.label.trim()
  let nextTitle = title.trim()
  if (!topic) {
    return nextTitle
  }

  for (const separator of [' - ', '：', ': ']) {
    const prefix = `${topic}${separator}`
    if (nextTitle.startsWith(prefix)) {
      nextTitle = nextTitle.slice(prefix.length).trim()
      break
    }
  }
  return nextTitle || title
}

function bookCoverText(title: string) {
  const clean = title.replace(/[^\p{L}\p{N}]/gu, '')
  return Array.from(clean).slice(0, 3).join('') || '书'
}

function friendlyChatError(error: unknown) {
  const message = error instanceof Error ? error.message : ''
  if (/503|not configured|api key|AI is not configured/i.test(message)) {
    return '模型服务暂不可用，请检查后端 API Key 配置。'
  }
  if (/超时|timeout|aborted/i.test(message)) {
    return '模型响应超时，请稍后重试。'
  }
  if (/Failed to fetch|NetworkError|Load failed/i.test(message)) {
    return '无法连接后端服务，请确认 FastAPI 已启动。'
  }
  return message ? `课程助手暂时无法回答：${message}` : '课程助手暂时无法回答，请稍后重试。'
}

function ResourceCenter() {
  const activeUserId = getActiveUserId()
  const notebook = useOutletContext<NotebookSummary | null>()
  const visitId = useNotebookVisitId()
  const graphShellRef = useRef<HTMLDivElement | null>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const dragStateRef = useRef<DragState | null>(null)
  const graphNodesRef = useRef<GraphNode[]>([])
  const graphEdgesRef = useRef<GraphEdge[]>([])
  const graphTransformRef = useRef({ x: 42, y: 32, scale: 1 })
  const nodeVelocityRef = useRef<Map<string, NodeVelocity>>(new Map())
  const simulationFrameRef = useRef<number | null>(null)
  const draggedNodeIdRef = useRef<string | null>(null)
  const typingTimerRef = useRef<number | null>(null)
  const pendingTypingRef = useRef<{ messageId: string; content: string } | null>(null)
  const chatThreadRef = useRef<HTMLDivElement | null>(null)
  const chatRequestIdRef = useRef(0)
  const graphUpdateRequestIdRef = useRef(0)
  const recommendationRequestIdRef = useRef(0)
  const skipNextAutoFitRef = useRef(false)

  const [courses, setCourses] = useState<CourseSummary[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState('')
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([])
  const [selectedKnowledgePointId, setSelectedKnowledgePointId] = useState('')
  const [graphTransform, setGraphTransform] = useState({ x: 42, y: 32, scale: 1 })
  const [tooltip, setTooltip] = useState<GraphTooltip | null>(null)
  const [hoveredEdgeId, setHoveredEdgeId] = useState('')
  const [graphLayoutVersion, setGraphLayoutVersion] = useState(0)
  const [isLoadingGraph, setIsLoadingGraph] = useState(false)
  const [isGeneratingGraph, setIsGeneratingGraph] = useState(false)
  const [isUpdatingGraph, setIsUpdatingGraph] = useState(false)
  const [isGraphFullscreen, setIsGraphFullscreen] = useState(false)
  const [graphError, setGraphError] = useState('')

  const [recommendations, setRecommendations] = useState<ResourceRecommendation[]>([])
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false)

  const [chatDraft, setChatDraft] = useState('')
  const [chatMessages, setChatMessages] = useNotebookSessionState<ChatMessage[]>(
    'resources:messages',
    [],
  )
  const [lastUserQuestion, setLastUserQuestion] = useState('')
  const [isChatting, setIsChatting] = useState(false)
  const [isTyping, setIsTyping] = useState(false)

  const selectedCourse = useMemo(
    () => courses.find((course) => course.id === selectedCourseId) || courses[0] || DEMO_COURSE,
    [courses, selectedCourseId],
  )
  const selectedNode = useMemo(
    () => graphNodes.find((node) => node.id === selectedKnowledgePointId) || graphNodes[0],
    [graphNodes, selectedKnowledgePointId],
  )
  const selectedNodeId = selectedNode?.id || ''
  const selectedNodeLabel = selectedNode?.label || ''
  const selectedRecommendationNode = useMemo<GraphNode | undefined>(() => {
    if (!selectedNodeId) {
      return undefined
    }
    return {
      id: selectedNodeId,
      label: selectedNodeLabel,
      description: '',
      chapter: '',
      importance: 'normal',
      mastery: 'unknown',
      order: 0,
      x: 0,
      y: 0,
    }
  }, [selectedNodeId, selectedNodeLabel])
  const nodeById = useMemo(() => new Map(graphNodes.map((node) => [node.id, node])), [graphNodes])
  const hasNotebook = Boolean(notebook?.notebook_id)
  const isDemoCourse = !hasNotebook && FALLBACK_COURSES.some((course) => course.id === selectedCourseId)
  const graphStorageId = notebook?.notebook_id || selectedCourseId

  useEffect(() => {
    graphTransformRef.current = graphTransform
  }, [graphTransform])

  useEffect(() => {
    graphNodesRef.current = graphNodes
    const nodeIds = new Set(graphNodes.map((node) => node.id))
    nodeVelocityRef.current.forEach((_, nodeId) => {
      if (!nodeIds.has(nodeId)) {
        nodeVelocityRef.current.delete(nodeId)
      }
    })
    graphNodes.forEach((node) => {
      if (!nodeVelocityRef.current.has(node.id)) {
        nodeVelocityRef.current.set(node.id, { vx: 0, vy: 0 })
      }
    })
  }, [graphNodes])

  useEffect(() => {
    graphEdgesRef.current = graphEdges
  }, [graphEdges])

  const applyDataset = useCallback((dataset: GraphDataset) => {
    nodeVelocityRef.current = new Map(dataset.nodes.map((node) => [node.id, { vx: 0, vy: 0 }]))
    setGraphNodes(dataset.nodes)
    setGraphEdges(dataset.edges)
    setSelectedKnowledgePointId((current) => {
      const currentNode = dataset.nodes.find((node) => node.id === current)
      const nextNode = currentNode || dataset.nodes.find((node) => node.importance === 'core') || dataset.nodes[0]
      return nextNode?.id || ''
    })
    setGraphLayoutVersion((current) => current + 1)
  }, [])

  const fitGraphView = useCallback(() => {
    const shell = graphShellRef.current
    const nodes = graphNodesRef.current
    if (!shell || nodes.length === 0) {
      return
    }

    const rect = shell.getBoundingClientRect()
    const graphPadding = 96
    const minX = Math.min(...nodes.map((node) => node.x)) - graphPadding
    const maxX = Math.max(...nodes.map((node) => node.x)) + graphPadding
    const minY = Math.min(...nodes.map((node) => node.y)) - graphPadding
    const maxY = Math.max(...nodes.map((node) => node.y)) + graphPadding
    const graphWidth = Math.max(1, maxX - minX)
    const graphHeight = Math.max(1, maxY - minY)
    const scale = clamp(
      Math.min(
        Math.max(1, rect.width - graphPadding) / graphWidth,
        Math.max(1, rect.height - graphPadding) / graphHeight,
      ),
      0.5,
      1.2,
    )

    setGraphTransform({
      x: (rect.width - graphWidth * scale) / 2 - minX * scale,
      y: (rect.height - graphHeight * scale) / 2 - minY * scale,
      scale,
    })
  }, [])

  const persistGraphSnapshot = useCallback(
    (nodes: GraphNode[], edges: GraphEdge[]) => {
      if (!graphStorageId || nodes.length === 0) {
        return
      }
      void courseApi
        .saveKnowledgeGraph(graphStorageId, {
          course_name: notebook?.title || selectedCourse?.name || null,
          graph: graphPayloadForUpdate(nodes, edges),
        })
        .catch((error) => console.warn('Knowledge graph save failed.', error))
    },
    [graphStorageId, notebook?.title, selectedCourse?.name],
  )

  const toggleGraphFullscreen = useCallback(() => {
    const updateFullscreen = () => setIsGraphFullscreen((current) => !current)
    const viewTransitionDocument = document as Document & {
      startViewTransition?: (update: () => void) => unknown
    }
    if (viewTransitionDocument.startViewTransition) {
      viewTransitionDocument.startViewTransition(updateFullscreen)
    } else {
      updateFullscreen()
    }
    window.setTimeout(fitGraphView, 280)
  }, [fitGraphView])

  const zoomGraphAt = useCallback((clientX: number, clientY: number, deltaY: number) => {
    const rect = svgRef.current?.getBoundingClientRect() || graphShellRef.current?.getBoundingClientRect()
    if (!rect) {
      return
    }

    const current = graphTransformRef.current
    const mouseX = clientX - rect.left
    const mouseY = clientY - rect.top
    const nextScale = clamp(current.scale * (deltaY > 0 ? 0.9 : 1.1), 0.48, 1.9)
    const graphX = (mouseX - current.x) / current.scale
    const graphY = (mouseY - current.y) / current.scale
    const nextTransform = {
      x: mouseX - graphX * nextScale,
      y: mouseY - graphY * nextScale,
      scale: nextScale,
    }

    graphTransformRef.current = nextTransform
    setGraphTransform(nextTransform)
  }, [])

  const startGraphSimulation = useCallback(() => {
    if (simulationFrameRef.current !== null) {
      return
    }

    let stableFrames = 0
    const tick = () => {
      let maxSpeed = 0

      setGraphNodes((current) => {
        if (current.length === 0) {
          return current
        }

        const velocities = nodeVelocityRef.current
        const draggedNodeId = draggedNodeIdRef.current
        const nodeMap = new Map(current.map((node) => [node.id, node]))
        const forces = new Map(current.map((node) => [node.id, { fx: 0, fy: 0 }]))

        graphEdgesRef.current.forEach((edge) => {
          const source = nodeMap.get(edge.source)
          const target = nodeMap.get(edge.target)
          if (!source || !target) {
            return
          }
          const dx = target.x - source.x
          const dy = target.y - source.y
          const distance = Math.max(1, Math.hypot(dx, dy))
          const desiredLength = edge.relation === 'advanced' ? 178 : 156
          const strength = 0.016
          const force = (distance - desiredLength) * strength
          const fx = (dx / distance) * force
          const fy = (dy / distance) * force
          const sourceForce = forces.get(source.id)
          const targetForce = forces.get(target.id)
          if (sourceForce) {
            sourceForce.fx += fx
            sourceForce.fy += fy
          }
          if (targetForce) {
            targetForce.fx -= fx
            targetForce.fy -= fy
          }
        })

        for (let leftIndex = 0; leftIndex < current.length; leftIndex += 1) {
          for (let rightIndex = leftIndex + 1; rightIndex < current.length; rightIndex += 1) {
            const left = current[leftIndex]
            const right = current[rightIndex]
            const dx = left.x - right.x
            const dy = left.y - right.y
            const distance = Math.max(16, Math.hypot(dx, dy))
            if (distance > 288) {
              continue
            }
            const force = (288 - distance) * 0.0038
            const fx = (dx / distance) * force
            const fy = (dy / distance) * force
            const leftForce = forces.get(left.id)
            const rightForce = forces.get(right.id)
            if (leftForce) {
              leftForce.fx += fx
              leftForce.fy += fy
            }
            if (rightForce) {
              rightForce.fx -= fx
              rightForce.fy -= fy
            }
          }
        }

        const layout = getGraphLayoutShape(current.length)
        const rows = Math.max(1, Math.ceil(current.length / layout.columns))
        const bounds = {
          minX: layout.originX - 116,
          maxX: layout.originX + (layout.columns - 1) * layout.horizontalGap + 116,
          minY: layout.originY - 116,
          maxY: layout.originY + (rows - 1) * layout.verticalGap + 132,
        }

        current.forEach((node) => {
          const force = forces.get(node.id)
          if (!force) {
            return
          }
          if (node.x < bounds.minX) {
            force.fx += (bounds.minX - node.x) * 0.006
          } else if (node.x > bounds.maxX) {
            force.fx -= (node.x - bounds.maxX) * 0.006
          }
          if (node.y < bounds.minY) {
            force.fy += (bounds.minY - node.y) * 0.006
          } else if (node.y > bounds.maxY) {
            force.fy -= (node.y - bounds.maxY) * 0.006
          }
        })

        const center = current.reduce(
          (total, node) => ({
            x: total.x + node.x / current.length,
            y: total.y + node.y / current.length,
          }),
          { x: 0, y: 0 },
        )
        const centerTarget = getGraphLayoutTarget(current.length)
        const centerForce = {
          fx: (centerTarget.x - center.x) * 0.0022,
          fy: (centerTarget.y - center.y) * 0.0022,
        }

        return current.map((node) => {
          if (node.id === draggedNodeId) {
            velocities.set(node.id, { vx: 0, vy: 0 })
            return node
          }

          const velocity = velocities.get(node.id) || { vx: 0, vy: 0 }
          const force = forces.get(node.id) || { fx: 0, fy: 0 }
          const nextVelocity = {
            vx: (velocity.vx + force.fx + centerForce.fx) * 0.86,
            vy: (velocity.vy + force.fy + centerForce.fy) * 0.86,
          }
          maxSpeed = Math.max(maxSpeed, Math.hypot(nextVelocity.vx, nextVelocity.vy))
          velocities.set(node.id, nextVelocity)

          if (Math.abs(nextVelocity.vx) < 0.01 && Math.abs(nextVelocity.vy) < 0.01) {
            return node
          }

          return {
            ...node,
            x: node.x + nextVelocity.vx,
            y: node.y + nextVelocity.vy,
          }
        })
      })

      if (draggedNodeIdRef.current || maxSpeed > 0.035) {
        stableFrames = 0
      } else {
        stableFrames += 1
      }

      if (stableFrames < 18) {
        simulationFrameRef.current = window.requestAnimationFrame(tick)
      } else {
        simulationFrameRef.current = null
      }
    }

    simulationFrameRef.current = window.requestAnimationFrame(tick)
  }, [])

  const generateGraph = useCallback(async () => {
    const fallbackGraph = fallbackGraphForCourse(selectedCourse)
    if (!graphStorageId || isDemoCourse) {
      applyDataset(datasetFromResponse(fallbackGraph))
      return
    }

    setIsGeneratingGraph(true)
    setGraphError('')
    try {
      const generated = await courseApi.generateKnowledgeGraph(graphStorageId)
      const dataset = datasetFromResponse(generated)
      if (dataset.nodes.length === 0) {
        throw new Error('empty graph')
      }
      applyDataset(dataset)
    } catch {
      setGraphError('')
      applyDataset(datasetFromResponse(fallbackGraph))
    } finally {
      setIsGeneratingGraph(false)
    }
  }, [applyDataset, graphStorageId, isDemoCourse, selectedCourse])

  const updateGraphWithAgent = useCallback(async () => {
    if (!graphStorageId || isUpdatingGraph) {
      return
    }

    const updateQuestion =
      lastUserQuestion || chatDraft.trim() || selectedNode?.label || selectedCourse?.name || ''
    const requestId = graphUpdateRequestIdRef.current + 1
    graphUpdateRequestIdRef.current = requestId

    const applyIncrementalDataset = (dataset: GraphDataset) => {
      const merged = mergeGraphPreserveLayout(
        graphNodesRef.current,
        graphEdgesRef.current,
        dataset,
        selectedNode?.id || selectedKnowledgePointId,
      )
      const nextVelocities = new Map(nodeVelocityRef.current)
      merged.nodes.forEach((node) => {
        if (!nextVelocities.has(node.id)) {
          nextVelocities.set(node.id, { vx: 0, vy: 0 })
        }
      })
      merged.nodeVelocitySeeds.forEach((velocity, nodeId) => {
        nextVelocities.set(nodeId, velocity)
      })
      nodeVelocityRef.current = nextVelocities
      graphNodesRef.current = merged.nodes
      graphEdgesRef.current = merged.edges
      skipNextAutoFitRef.current = true
      setGraphNodes(merged.nodes)
      setGraphEdges(merged.edges)
      setSelectedKnowledgePointId((current) => {
        if (merged.nodes.some((node) => node.id === current)) {
          return current
        }
        return selectedNode?.id || merged.addedNodeIds[0] || merged.nodes[0]?.id || ''
      })
      console.debug('knowledge graph incremental merge', {
        course_id: graphStorageId,
        selected_node_id: selectedNode?.id || selectedKnowledgePointId,
        added_node_ids: merged.addedNodeIds,
        added_edge_ids: merged.addedEdgeIds,
      })
      startGraphSimulation()
    }

    setIsUpdatingGraph(true)
    setGraphError('')

    if (isDemoCourse) {
      applyIncrementalDataset(
        localExpansionDataset(selectedCourse, selectedNode, updateQuestion, graphNodesRef.current),
      )
      setIsUpdatingGraph(false)
      return
    }

    try {
      const updated = await courseApi.updateKnowledgeGraph(graphStorageId, {
        course_name: notebook?.title || selectedCourse?.name || null,
        selected_node_id: selectedNode?.id || null,
        selected_node_name: selectedNode?.label || null,
        user_question: updateQuestion,
        current_graph: graphPayloadForUpdate(graphNodesRef.current, graphEdgesRef.current),
      })
      if (graphUpdateRequestIdRef.current !== requestId) {
        return
      }
      const dataset = datasetFromUpdateResponse(updated, graphNodesRef.current)
      if (dataset.nodes.length === 0 && dataset.edges.length === 0) {
        throw new Error('empty graph')
      }
      applyIncrementalDataset(dataset)
    } catch (error) {
      if (graphUpdateRequestIdRef.current === requestId) {
        console.warn('Knowledge graph incremental update failed.', error)
        setGraphError('\u667a\u80fd\u6269\u5c55\u5931\u8d25\uff0c\u5df2\u4fdd\u7559\u5f53\u524d\u56fe\u8c31\u3002')
      }
    } finally {
      if (graphUpdateRequestIdRef.current === requestId) {
        setIsUpdatingGraph(false)
      }
    }
  }, [
    chatDraft,
    graphStorageId,
    isDemoCourse,
    isUpdatingGraph,
    lastUserQuestion,
    notebook?.title,
    selectedCourse,
    selectedKnowledgePointId,
    selectedNode,
    startGraphSimulation,
  ])

  useEffect(() => {
    let isActive = true
    const matchedCourse = fallbackCourseForNotebookTitle(notebook?.title)

    async function loadCourses() {
      try {
        const nextCourses = await courseApi.list()
        if (!isActive) {
          return
        }
        const usableCourses = mergeCoursesWithFallback(nextCourses)
        setCourses(usableCourses)
        setSelectedCourseId(matchedCourse.id)
      } catch {
        if (!isActive) {
          return
        }
        setCourses(FALLBACK_COURSES)
        setSelectedCourseId(matchedCourse.id)
      }
    }

    loadCourses()
    return () => {
      isActive = false
    }
  }, [notebook?.title])

  useEffect(() => {
    if (!selectedCourseId) {
      return
    }

    let isActive = true

    async function loadGraph() {
      setIsLoadingGraph(true)
      setGraphError('')
      const fallbackGraph = fallbackGraphForCourse(selectedCourse)

      if (graphStorageId) {
        try {
          const storedGraph = await courseApi.knowledgeGraph(graphStorageId)
          const storedDataset = datasetFromResponse(storedGraph)
          if (storedDataset.nodes.length > 0) {
            if (isActive) {
              applyDataset(storedDataset)
              setIsLoadingGraph(false)
            }
            return
          }
        } catch {
          // The first visit has no stored graph yet; continue with the course graph.
        }
      }

      if (hasNotebook && graphStorageId) {
        try {
          const generated = await courseApi.generateKnowledgeGraph(graphStorageId)
          const generatedDataset = datasetFromResponse(generated)
          if (generatedDataset.nodes.length === 0) {
            throw new Error('empty graph')
          }
          if (isActive) {
            applyDataset(generatedDataset)
            setIsLoadingGraph(false)
          }
        } catch {
          if (isActive) {
            setGraphError('')
            applyDataset(datasetFromResponse(fallbackGraph))
            setIsLoadingGraph(false)
          }
        }
        return
      }

      if (isDemoCourse) {
        if (isActive) {
          applyDataset(datasetFromResponse(fallbackGraph))
          setIsLoadingGraph(false)
        }
        return
      }

      try {
        const graph = await courseApi.knowledgeGraph(selectedCourseId)
        const dataset = datasetFromResponse(graph)
        if (dataset.nodes.length === 0) {
          const generated = await courseApi.generateKnowledgeGraph(selectedCourseId)
          const generatedDataset = datasetFromResponse(generated)
          if (generatedDataset.nodes.length === 0) {
            throw new Error('empty graph')
          }
          if (isActive) {
            applyDataset(generatedDataset)
          }
        } else if (isActive) {
          applyDataset(dataset)
        }
      } catch {
        if (isActive) {
          setGraphError('')
          applyDataset(datasetFromResponse(fallbackGraph))
        }
      } finally {
        if (isActive) {
          setIsLoadingGraph(false)
        }
      }
    }

    loadGraph()
    return () => {
      isActive = false
    }
  }, [applyDataset, graphStorageId, hasNotebook, isDemoCourse, selectedCourse, selectedCourseId])

  useEffect(() => {
    if (graphNodes.length === 0) {
      return
    }
    if (skipNextAutoFitRef.current) {
      skipNextAutoFitRef.current = false
      return
    }
    const timer = window.setTimeout(fitGraphView, 80)
    return () => window.clearTimeout(timer)
  }, [fitGraphView, graphLayoutVersion, graphNodes.length])

  useEffect(() => {
    if (!graphStorageId || isLoadingGraph || graphNodes.length === 0) {
      return
    }
    const timer = window.setTimeout(() => {
      persistGraphSnapshot(graphNodes, graphEdges)
    }, 850)
    return () => window.clearTimeout(timer)
  }, [graphEdges, graphNodes, graphStorageId, isLoadingGraph, persistGraphSnapshot])

  useEffect(
    () => () => {
      persistGraphSnapshot(graphNodesRef.current, graphEdgesRef.current)
    },
    [persistGraphSnapshot],
  )

  useEffect(() => {
    if (!isGraphFullscreen) {
      return
    }
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        toggleGraphFullscreen()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isGraphFullscreen, toggleGraphFullscreen])

  useEffect(
    () => () => {
      if (simulationFrameRef.current !== null) {
        window.cancelAnimationFrame(simulationFrameRef.current)
      }
      if (typingTimerRef.current !== null) {
        window.clearInterval(typingTimerRef.current)
      }
      const pending = pendingTypingRef.current
      if (pending) {
        setChatMessages((current) =>
          current.map((message) =>
            message.id === pending.messageId
              ? { ...message, content: pending.content }
              : message,
          ),
        )
      }
    },
    [setChatMessages],
  )

  useEffect(() => {
    const shell = graphShellRef.current
    if (!shell) {
      return undefined
    }

    const handleGraphWheel = (event: globalThis.WheelEvent) => {
      event.preventDefault()
      event.stopPropagation()
      zoomGraphAt(event.clientX, event.clientY, event.deltaY)
    }

    shell.addEventListener('wheel', handleGraphWheel, { passive: false })
    return () => {
      shell.removeEventListener('wheel', handleGraphWheel)
    }
  }, [zoomGraphAt])

  useEffect(() => {
    const thread = chatThreadRef.current
    if (!thread) {
      return
    }
    window.requestAnimationFrame(() => {
      thread.scrollTop = thread.scrollHeight
    })
  }, [chatMessages, isChatting, isTyping])

  useEffect(() => {
    const fallbackItems = recommendationFallback(selectedCourse, selectedRecommendationNode)
    const topic = selectedRecommendationNode?.label || notebook?.title || selectedCourse?.name || '当前课程'
    if (selectedCourseId) {
      setRecommendations(fallbackItems)
    } else {
      setRecommendations([])
    }

    if (!selectedCourseId || !notebook?.notebook_id) {
      setIsLoadingRecommendations(false)
      return
    }

    let isCurrent = true
    const requestId = recommendationRequestIdRef.current + 1
    recommendationRequestIdRef.current = requestId
    setIsLoadingRecommendations(true)

    void classroomApi
      .profile({
        user_id: activeUserId,
        course_id: notebook.course_id,
        notebook_id: notebook.notebook_id,
      })
      .then((profile) => {
        if (!isCurrent || recommendationRequestIdRef.current !== requestId) {
          return
        }
        const profileResources = (profile.learning_resources || []).map((item, index) =>
          profileResourceToRecommendation(item, index, topic),
        )
        setRecommendations(profileResources.length > 0 ? profileResources.slice(0, 7) : fallbackItems)
      })
      .catch((error) => {
        if (!isCurrent || recommendationRequestIdRef.current !== requestId) {
          return
        }
        console.warn('Resource recommendations failed.', error)
        setRecommendations(fallbackItems)
      })
      .finally(() => {
        if (isCurrent && recommendationRequestIdRef.current === requestId) {
          setIsLoadingRecommendations(false)
        }
      })

    return () => {
      isCurrent = false
    }
  }, [
    activeUserId,
    notebook?.notebook_id,
    notebook?.course_id,
    notebook?.title,
    selectedCourse,
    selectedCourseId,
    selectedRecommendationNode,
  ])

  function updateTooltip(event: PointerEvent, node: GraphNode) {
    const rect = graphShellRef.current?.getBoundingClientRect()
    setTooltip({
      type: 'node',
      node,
      x: event.clientX - (rect?.left ?? 0) + 12,
      y: event.clientY - (rect?.top ?? 0) + 12,
    })
  }

  function updateEdgeTooltip(event: PointerEvent, edge: GraphEdge) {
    const source = nodeById.get(edge.source)
    const target = nodeById.get(edge.target)
    if (!source || !target) {
      return
    }
    const rect = graphShellRef.current?.getBoundingClientRect()
    setHoveredEdgeId(edge.id)
    setTooltip({
      type: 'edge',
      edge,
      source,
      target,
      x: event.clientX - (rect?.left ?? 0) + 12,
      y: event.clientY - (rect?.top ?? 0) + 12,
    })
  }

  function handleSvgPointerDown(event: PointerEvent<SVGSVGElement>) {
    event.currentTarget.setPointerCapture(event.pointerId)
    dragStateRef.current = {
      mode: 'pan',
      startClientX: event.clientX,
      startClientY: event.clientY,
      startTranslateX: graphTransform.x,
      startTranslateY: graphTransform.y,
    }
  }

  function handleNodePointerDown(event: PointerEvent<SVGGElement>, node: GraphNode) {
    event.stopPropagation()
    event.currentTarget.ownerSVGElement?.setPointerCapture(event.pointerId)
    dragStateRef.current = {
      mode: 'node',
      nodeId: node.id,
      hasDragged: false,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startTranslateX: graphTransformRef.current.x,
      startTranslateY: graphTransformRef.current.y,
      startNodeX: node.x,
      startNodeY: node.y,
    }
  }

  function handleSvgPointerMove(event: PointerEvent<SVGSVGElement>) {
    const dragState = dragStateRef.current
    if (!dragState) {
      return
    }

    if (dragState.mode === 'pan') {
      setGraphTransform((current) => ({
        ...current,
        x: dragState.startTranslateX + event.clientX - dragState.startClientX,
        y: dragState.startTranslateY + event.clientY - dragState.startClientY,
      }))
      return
    }

    const movementX = event.clientX - dragState.startClientX
    const movementY = event.clientY - dragState.startClientY
    const movement = Math.hypot(movementX, movementY)
    if (!dragState.hasDragged && movement <= 5) {
      return
    }

    if (!dragState.hasDragged) {
      dragState.hasDragged = true
      draggedNodeIdRef.current = dragState.nodeId || null
      if (dragState.nodeId) {
        nodeVelocityRef.current.set(dragState.nodeId, { vx: 0, vy: 0 })
      }
      startGraphSimulation()
    }

    const deltaX = movementX / graphTransformRef.current.scale
    const deltaY = movementY / graphTransformRef.current.scale
    setGraphNodes((current) =>
      current.map((node) =>
        node.id === dragState.nodeId
          ? {
              ...node,
              x: (dragState.startNodeX ?? node.x) + deltaX,
              y: (dragState.startNodeY ?? node.y) + deltaY,
            }
          : node,
      ),
    )
    startGraphSimulation()
  }

  function handlePointerUp(event: PointerEvent<SVGSVGElement>) {
    const dragState = dragStateRef.current
    if (dragState && event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    if (dragState?.mode === 'node' && dragState.nodeId && !dragState.hasDragged) {
      setSelectedKnowledgePointId(dragState.nodeId)
    }
    dragStateRef.current = null
    draggedNodeIdRef.current = null
    if (dragState?.hasDragged) {
      startGraphSimulation()
      persistGraphSnapshot(graphNodesRef.current, graphEdgesRef.current)
    }
  }

  function handleShelfWheel(event: WheelEvent<HTMLDivElement>) {
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
      return
    }
    event.currentTarget.scrollLeft += event.deltaY
    event.preventDefault()
  }

  function stopTyping(completeMessage = true) {
    if (typingTimerRef.current !== null) {
      window.clearInterval(typingTimerRef.current)
      typingTimerRef.current = null
    }
    const pending = pendingTypingRef.current
    if (completeMessage && pending) {
      setChatMessages((current) =>
        current.map((message) =>
          message.id === pending.messageId
            ? { ...message, content: pending.content }
            : message,
        ),
      )
    }
    pendingTypingRef.current = null
    setIsTyping(false)
  }

  function startTypewriter(content: string) {
    stopTyping()
    const messageId = `assistant-${Date.now()}`
    const chars = Array.from(content || 'AI did not return content.')
    let index = 0
    pendingTypingRef.current = { messageId, content: chars.join('') }

    setIsTyping(true)
    setChatMessages((current) => [
      ...current,
      {
        id: messageId,
        role: 'assistant',
        content: '',
      },
    ])

    typingTimerRef.current = window.setInterval(() => {
      index = Math.min(index + 2, chars.length)
      const nextContent = chars.slice(0, index).join('')
      setChatMessages((current) =>
        current.map((message) =>
          message.id === messageId ? { ...message, content: nextContent } : message,
        ),
      )

      if (index >= chars.length) {
        stopTyping()
      }
    }, 24)
  }

  async function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const question = chatDraft.trim()
    if (!question || isChatting || isTyping) {
      return
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
    }
    setChatMessages((current) => [...current, userMessage])
    setChatDraft('')
    setIsChatting(true)
    const requestId = chatRequestIdRef.current + 1
    chatRequestIdRef.current = requestId

    try {
      const answer = await tutorApi.ask({
        user_id: activeUserId,
        notebook_id: notebook?.notebook_id || null,
        visit_id: visitId,
        course_id: null,
        course_name: notebook?.title || selectedCourse?.name || null,
        knowledge_point_id: isDemoCourse ? null : selectedNode?.id || null,
        knowledge_point_name: selectedNode?.label || null,
        question,
        student_profile: {
          current_course: notebook?.title || selectedCourse?.name,
          current_knowledge_point: selectedNode?.label,
        },
      })
      const answerPayload = answer as typeof answer & {
        content?: string
        message?: string
        response?: string
      }
      const assistantContent =
        pickString(
          answerPayload.answer,
          answerPayload.content,
          answerPayload.message,
          answerPayload.response,
        ) || 'AI did not return content.'
      if (chatRequestIdRef.current !== requestId) {
        return
      }
      setLastUserQuestion(question)
      setIsChatting(false)
      startTypewriter(assistantContent)
    } catch (error) {
      if (chatRequestIdRef.current !== requestId) {
        return
      }
      console.warn('Tutor request failed.', error)
      setChatMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: friendlyChatError(error),
        },
      ])
    } finally {
      if (chatRequestIdRef.current === requestId) {
        setIsChatting(false)
      }
    }
  }

  return (
    <div className={`page resource-workbench${isGraphFullscreen ? ' is-graph-fullscreen' : ''}`}>
      <div className="resource-workbench-grid">
        <section
          className={`panel knowledge-graph-panel${isGraphFullscreen ? ' is-fullscreen' : ''}`}
        >
          <div className="resource-panel-header">
            <div>
              <h2>课程知识图谱</h2>
            </div>
            <div className="resource-panel-actions">
              <button
                className="graph-icon-button"
                type="button"
                onClick={toggleGraphFullscreen}
                title={isGraphFullscreen ? '退出全屏' : '全屏查看'}
                aria-label={isGraphFullscreen ? '退出全屏' : '全屏查看'}
              >
                {isGraphFullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
              </button>
              <button
                className="graph-icon-button"
                type="button"
                onClick={generateGraph}
                disabled={isGeneratingGraph || isUpdatingGraph}
                title="重新生成图谱"
                aria-label="重新生成图谱"
              >
                <RefreshCw size={17} />
              </button>
              <button
                className="graph-icon-button graph-smart-button"
                type="button"
                onClick={updateGraphWithAgent}
                disabled={isLoadingGraph || isGeneratingGraph || isUpdatingGraph}
                title="智能更新知识图谱"
                aria-label="智能更新知识图谱"
              >
                {isUpdatingGraph ? <RefreshCw size={17} /> : <Sparkles size={17} />}
              </button>
            </div>
          </div>

          <div className="graph-legend" aria-label="图例">
            {graphLegendItems.map((item) => (
              <span className={item.className} key={item.label}>
                <i />
                {item.label}
              </span>
            ))}
          </div>

          {graphError ? <p className="resource-inline-error">{graphError}</p> : null}

          <div className="knowledge-graph-canvas" ref={graphShellRef}>
            {isLoadingGraph ? (
              <div className="resource-loading-state">图谱加载中...</div>
            ) : graphNodes.length === 0 ? (
              <div className="resource-empty-state">暂无图谱数据</div>
            ) : (
              <svg
                ref={svgRef}
                role="img"
                aria-label={`${selectedCourse?.name || '课程'}知识图谱`}
                onPointerDown={handleSvgPointerDown}
                onPointerMove={handleSvgPointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerUp}
              >
                <g
                  transform={`translate(${graphTransform.x} ${graphTransform.y}) scale(${graphTransform.scale})`}
                >
                  {graphEdges.map((edge) => {
                    const source = nodeById.get(edge.source)
                    const target = nodeById.get(edge.target)
                    if (!source || !target) {
                      return null
                    }
                    return (
                      <g key={edge.id}>
                        <line
                          className="graph-edge-hit"
                          x1={source.x}
                          y1={source.y}
                          x2={target.x}
                          y2={target.y}
                          onPointerEnter={(event) => updateEdgeTooltip(event, edge)}
                          onPointerMove={(event) => updateEdgeTooltip(event, edge)}
                          onPointerLeave={() => {
                            setHoveredEdgeId('')
                            setTooltip(null)
                          }}
                        />
                        <line
                          className={`graph-edge is-${edge.relation} ${
                            hoveredEdgeId === edge.id ? 'is-hovered' : ''
                          }`}
                          x1={source.x}
                          y1={source.y}
                          x2={target.x}
                          y2={target.y}
                        />
                      </g>
                    )
                  })}

                  {graphNodes.map((node) => {
                    const radius = getNodeRadius(node)
                    const lines = labelLines(node.label)
                    return (
                      <g
                        className={`graph-node is-${node.importance} ${
                          selectedKnowledgePointId === node.id ? 'is-current' : ''
                        }`}
                        key={node.id}
                        tabIndex={0}
                        transform={`translate(${node.x} ${node.y})`}
                        onPointerDown={(event) => handleNodePointerDown(event, node)}
                        onPointerEnter={(event) => updateTooltip(event, node)}
                        onPointerMove={(event) => updateTooltip(event, node)}
                        onPointerLeave={() => setTooltip(null)}
                      >
                        <circle r={radius} />
                        {lines.map((line, index) => (
                          <text key={line} y={lines.length === 1 ? 5 : index === 0 ? -3 : 14}>
                            {line}
                          </text>
                        ))}
                      </g>
                    )
                  })}
                </g>
              </svg>
            )}

            {tooltip ? (
              <div
                className={`graph-tooltip is-${tooltip.type}`}
                style={{
                  left: tooltip.x,
                  top: tooltip.y,
                }}
              >
                {tooltip.type === 'node' ? (
                  <>
                    <strong>{tooltip.node.label}</strong>
                    <dl>
                      <div>
                        <dt>重要程度</dt>
                        <dd>{importanceLabel(tooltip.node.importance)}</dd>
                      </div>
                      <div>
                        <dt>掌握状态</dt>
                        <dd>{masteryLabel(tooltip.node.mastery)}</dd>
                      </div>
                    </dl>
                    <p>{tooltip.node.description || '暂无简介'}</p>
                    <em>点击后查看该知识点资源</em>
                  </>
                ) : (
                  <>
                    <strong>
                      {tooltip.source.label} → {tooltip.target.label}
                    </strong>
                    <span>{relationLabel(tooltip.edge.relation)}</span>
                    <p>{edgeDescription(tooltip.edge, tooltip.source, tooltip.target)}</p>
                  </>
                )}
              </div>
            ) : null}
          </div>
        </section>

        <div className="resource-right-stack">
          <section className="panel recommendation-panel">
            <div className="resource-panel-header">
              <div>
                <h2>推荐学习资源</h2>
              </div>
            </div>

            <div className="book-shelf-grid resource-shelf" onWheel={handleShelfWheel}>
              {isLoadingRecommendations
                ? Array.from({ length: 4 }).map((_, index) => (
                    <div className="resource-book-card is-skeleton" key={index}>
                      <div className="resource-book-cover" />
                      <span />
                    </div>
                  ))
                : recommendations.map((item) => {
                    const displayTitle = displayResourceTitle(item.title, selectedNode)
                    const card = (
                      <>
                        <div className="resource-book-cover">
                          {item.cover_url ? (
                            <img src={item.cover_url} alt="" loading="lazy" />
                          ) : (
                            <span>{bookCoverText(displayTitle)}</span>
                          )}
                        </div>
                        <strong className="resource-book-title" title={displayTitle}>
                          {displayTitle}
                        </strong>
                      </>
                    )

                    return item.url ? (
                      <a
                        className="resource-book-card"
                        href={item.url}
                        key={item.id}
                        rel="noreferrer"
                        target="_blank"
                        title={displayTitle}
                      >
                        {card}
                      </a>
                    ) : (
                      <article className="resource-book-card" key={item.id} title={displayTitle}>
                        {card}
                      </article>
                    )
                  })}
            </div>
          </section>

          <section className="panel resource-chat-panel">
            <div className="resource-panel-header">
              <div>
                <h2>课程学习助手</h2>
                <p>
                  当前：{selectedCourse?.name || '课程'}
                  {selectedNode ? ` / ${selectedNode.label}` : ''}
                </p>
              </div>
              <button
                className="graph-icon-button"
                type="button"
                onClick={() => {
                  chatRequestIdRef.current += 1
                  stopTyping(false)
                  setIsChatting(false)
                  setChatMessages([])
                  setLastUserQuestion('')
                }}
                title="清空对话"
                aria-label="清空对话"
              >
                <Trash2 size={17} />
              </button>
            </div>

            <div className="resource-chat-thread" ref={chatThreadRef} aria-live="polite">
              {chatMessages.length === 0 ? (
                <div className="resource-chat-empty">
                  <BotMessageSquare size={24} />
                  <span>可以围绕当前课程或知识点提问。</span>
                </div>
              ) : (
                chatMessages.map((item, index) => (
                  <article
                    className={`resource-chat-message ${item.role} ${
                      isTyping && item.role === 'assistant' && index === chatMessages.length - 1
                        ? 'is-typing'
                        : ''
                    }`}
                    key={item.id}
                  >
                    {item.role === 'assistant' && item.content ? (
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p>{item.content}</p>
                    )}
                  </article>
                ))
              )}
              {isChatting ? (
                <article className="resource-chat-message assistant is-loading">
                  <span>思考中...</span>
                </article>
              ) : null}
            </div>

            <form className="resource-chat-composer" onSubmit={handleChatSubmit}>
              <textarea
                value={chatDraft}
                disabled={isChatting || isTyping}
                onChange={(event) => setChatDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    event.currentTarget.form?.requestSubmit()
                  }
                }}
                placeholder="输入你的课程问题"
              />
              <button type="submit" disabled={isChatting || isTyping || chatDraft.trim().length === 0}>
                <Send size={18} />
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  )
}

export default ResourceCenter
