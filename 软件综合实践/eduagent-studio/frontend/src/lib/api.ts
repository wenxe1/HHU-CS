const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE_URL = (rawApiBaseUrl ?? '').replace(/\/$/, '')

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export type ResourceType = 'lecture' | 'exercise' | 'mindmap' | 'slide' | 'code_lab'
export type AuditStatus = 'pending' | 'approved' | 'rejected'
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface CourseSummary {
  id: string
  name: string
  description?: string | null
  teacher_id?: string | null
  created_at?: string
}

export interface NotebookSummary {
  notebook_id: string
  user_id: string
  title: string
  course_id: string
  knowledge_point_id: string
  source_count: number
  recommended_resources?: ResourceRecommendation[]
  created_at: string
  updated_at: string
}

export interface KnowledgePointSummary {
  id: string
  course_id: string
  chapter?: string | null
  name: string
  description?: string | null
  difficulty: string
  prerequisites: string[]
  order: number
  created_at?: string
}

export interface KnowledgeGraphNode {
  id?: string
  name?: string
  label?: string
  title?: string
  chapter?: string | null
  description?: string | null
  difficulty?: string
  importance?: 'core' | 'important' | 'normal' | string
  mastery?: 'unknown' | 'weak' | 'medium' | 'mastered' | string
  prerequisites?: Array<string | { id?: string; name?: string }>
  order?: number
  x?: number
  y?: number
  [key: string]: unknown
}

export interface KnowledgeGraphEdge {
  id?: string
  source: string
  target: string
  relation?: 'prerequisite' | 'related' | 'advanced' | string
  description?: string | null
  reason?: string | null
}

export interface KnowledgeGraphResult {
  course_id: string
  course_name: string
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  source?: 'agent' | 'database' | 'fallback' | 'local' | string
  updated_reason?: string
  added_node_ids?: string[]
  updated_node_ids?: string[]
  added_edge_ids?: string[]
}

export type KnowledgeGraphResponse = KnowledgeGraphNode[] | KnowledgeGraphResult

export interface KnowledgeGraphUpdateRequest {
  course_name?: string | null
  selected_node_id?: string | null
  selected_node_name?: string | null
  user_question?: string | null
  current_graph?: {
    nodes: Array<
      Pick<
        KnowledgeGraphNode,
        'id' | 'label' | 'description' | 'importance' | 'mastery' | 'chapter' | 'order' | 'x' | 'y'
      >
    >
    edges: KnowledgeGraphEdge[]
  }
}

export interface ResourceGenerateRequest {
  user_id: string
  course_id: string
  knowledge_point_id: string
  resource_types: ResourceType[]
}

export interface ResourceGenerateResult {
  task_id: string
  status: TaskStatus
  resource_ids: string[]
}

export interface ResourceListParams {
  user_id?: string
  course_id?: string
  knowledge_point_id?: string
  type?: ResourceType
}

export interface LearningResourceSummary {
  resource_id: string
  task_id: string
  user_id: string
  course_id: string
  knowledge_point_id: string
  type: ResourceType
  title: string
  audit_status: AuditStatus
  created_at: string
}

export interface ResourceListResult {
  items: LearningResourceSummary[]
  total: number
}

export interface ResourceRecommendationParams {
  course_id: string
  course_name?: string
  knowledge_point_id?: string
  query?: string
}

export interface ResourceRecommendation {
  id: string
  title: string
  authors: string[]
  source: string
  cover_url: string
  description: string
  level: string
  tags: string[]
  related_knowledge_points: string[]
  reason: string
  url: string
}

export interface ResourceRecommendationResult {
  items: ResourceRecommendation[]
  source: 'web' | 'fallback' | 'database' | string
  course_name?: string
  query?: string
  knowledge_point_id?: string | null
  debug?: Record<string, unknown>
}

export interface LearningResourceDetail extends LearningResourceSummary {
  content: Record<string, unknown>
  updated_at: string
}

export interface TaskEvent {
  stage: string
  message: string
  progress: number
  created_at: string
}

export interface AgentTask {
  task_id: string
  user_id: string
  course_id: string
  knowledge_point_id: string
  status: TaskStatus
  progress: number
  current_stage: string
  events: TaskEvent[]
  resource_ids: string[]
  created_at: string
  updated_at: string
}

export interface TutorAskRequest {
  user_id: string
  question: string
  course_id?: string | null
  course_name?: string | null
  notebook_id?: string | null
  visit_id?: string | null
  knowledge_point_id?: string | null
  knowledge_point_name?: string | null
  source_document_ids?: string[]
  student_profile?: Record<string, unknown>
  code_snippet?: string | null
}

export interface TutorAskResult {
  session_id: string
  answer: string
  guidance_steps: string[]
  follow_up_questions: string[]
  citations?: Array<{
    source_id: string
    document_id: string
    source_title: string
    chunk_index: number
  }>
  personalization: Record<string, unknown>
}

export interface TutorPreviewResult {
  preview_type: 'pdf'
  preview_url: string
  filename: string
  original_type: 'pdf' | string
}

export interface CodeReviewRequest {
  user_id: string
  language: string
  code: string
  course_id?: string | null
  knowledge_point_id?: string | null
  error_message?: string | null
}

export interface CodeReviewIssue {
  category: string
  severity: string
  title: string
  detail: string
  suggestion: string
  line?: number | null
}

export interface CodeReviewResult {
  record_id: string
  language: string
  summary: string
  issues: CodeReviewIssue[]
  suggestions: string[]
  next_steps: string[]
}

export interface ClassroomGenerateRequest {
  user_id: string
  course_id: string
  notebook_id?: string | null
  knowledge_point_id: string
  topic?: string | null
  source_document_ids?: string[]
}

export interface ClassroomGenerateResult {
  session_id: string
  title: string
  status: TaskStatus
  scene_count: number
  scene_types: string[]
}

export interface ClassroomScene {
  scene_id: string
  session_id: string
  scene_type: string
  title: string
  content: Record<string, unknown>
  order: number
  speaker?: string | null
  actions: Array<Record<string, unknown>>
  created_at: string
}

export interface ClassroomDetail {
  session_id: string
  user_id: string
  course_id: string
  knowledge_point_id: string
  title: string
  description: string
  learning_goals: string[]
  agents: Array<Record<string, unknown>>
  status: string
  scene_ids: string[]
  scenes: ClassroomScene[]
  created_at: string
  updated_at: string
}

export interface RAGDocumentSummary {
  document_id: string
  source_id: string
  user_id: string
  course_id: string
  notebook_id: string
  filename: string
  source_title: string
  source_content?: string
  content_type: string
  source_type: string
  upload_status: 'processing' | 'success' | 'failed'
  processing_error?: string | null
  chunk_count: number
  metadata: Record<string, string>
  created_at: string
  updated_at: string
}

export interface RAGDocumentListResult {
  items: RAGDocumentSummary[]
  total: number
}

export interface RAGUploadResult {
  document_id: string
  source_id: string
  upload_status: 'processing' | 'success' | 'failed'
  chunk_count: number
  document?: RAGDocumentSummary | null
  chunks: Array<{
    chunk_id: string
    chunk_index: number
    preview: string
  }>
}

export interface QuizQuestion {
  question_id: string
  type: 'single_choice'
  stem: string
  options: string[]
  answer: string
  explanation: string
  option_explanations?: Record<string, string>
}

export interface ClassroomQuizGenerateRequest {
  user_id: string
  course_id: string
  notebook_id?: string | null
  knowledge_point_id?: string | null
  source_document_ids: string[]
  question_count?: number
  difficulty?: 'easy' | 'medium' | 'hard'
}

export interface ClassroomQuizGenerateResult {
  quiz_id: string
  user_id?: string
  course_id?: string
  notebook_id?: string | null
  knowledge_point_id?: string | null
  title: string
  questions: QuizQuestion[]
  source_document_ids: string[]
  created_at?: string
  updated_at?: string
}

export interface QuizPracticeRecordRequest {
  user_id: string
  course_id: string
  quiz_id: string
  question_id: string
  selected_answer: string
}

export interface QuizPracticeRecord {
  record_id: string
  user_id: string
  course_id: string
  notebook_id?: string | null
  quiz_id: string
  question_id: string
  selected_answer: string
  correct_answer: string
  is_correct: boolean
  created_at: string
  updated_at: string
}

export interface FlashcardItem {
  card_id: string
  front: string
  back: string
}

export interface ClassroomFlashcardsGenerateRequest {
  user_id: string
  course_id: string
  notebook_id?: string | null
  knowledge_point_id?: string | null
  source_document_ids: string[]
  card_count?: number
  difficulty?: 'easy' | 'medium' | 'hard'
}

export interface ClassroomFlashcardsGenerateResult {
  flashcard_set_id: string
  user_id?: string
  course_id?: string
  notebook_id?: string | null
  knowledge_point_id?: string | null
  title: string
  cards: FlashcardItem[]
  source_document_ids: string[]
  created_at?: string
  updated_at?: string
}

export type FlashcardPracticeResult = 'correct' | 'incorrect'

export interface FlashcardPracticeRecord {
  record_id: string
  user_id: string
  course_id: string
  flashcard_set_id: string
  attempt_id: string
  study_card_ids: string[]
  card_id: string
  result: FlashcardPracticeResult
  attempt_completed: boolean
  created_at: string
  updated_at: string
}

export interface ClassroomStudioListResult {
  quizzes: ClassroomQuizGenerateResult[]
  flashcard_sets: ClassroomFlashcardsGenerateResult[]
  flashcard_records: FlashcardPracticeRecord[]
}

export interface FlashcardPracticeRecordRequest {
  user_id: string
  course_id: string
  flashcard_set_id: string
  attempt_id: string
  study_card_ids: string[]
  card_id: string
  result: FlashcardPracticeResult
}

export interface UserProfileRadarMetric {
  key: string
  label: string
  score: number
  reason: string
}

export interface UserProfileRecommendation {
  title: string
  detail: string
  priority: 'high' | 'medium' | 'low' | string
}

export interface UserProfileLearningResource {
  title: string
  url: string
  language: 'zh' | 'en' | string
  reason: string
}

export interface UserProfileSignals {
  conversation_count: number
  message_count: number
  quiz_attempt_count: number
  flashcard_attempt_count: number
  quiz_accuracy: number
  flashcard_accuracy: number
}

export interface UserProfileWindow {
  conversation_limit: number
  quiz_practice_limit: number
  flashcard_practice_limit: number
}

export interface UserProfileResult {
  user_id: string
  course_id: string
  notebook_id?: string | null
  is_unlocked: boolean
  generated_at: string
  window: UserProfileWindow
  signals: UserProfileSignals
  summary: string
  radar: UserProfileRadarMetric[]
  learning_traits: string[]
  strengths: string[]
  risks: string[]
  recommendations: UserProfileRecommendation[]
  learning_resources: UserProfileLearningResource[]
}

export interface UserProfileGenerateRequest {
  user_id: string
  course_id: string
  notebook_id?: string | null
  force_refresh?: boolean
}

type QueryValue = string | number | null | undefined
type RequestOptions = RequestInit & {
  timeoutMs?: number
  timeoutMessage?: string
}

export function resolveApiUrl(pathOrUrl: string) {
  if (/^(https?:|blob:|data:)/i.test(pathOrUrl)) {
    return pathOrUrl
  }

  const path = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path
}

function buildQuery(params: Record<string, QueryValue>) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).length > 0) {
      query.set(key, String(value))
    }
  })

  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { timeoutMs, timeoutMessage, ...requestInit } = init
  const controller = timeoutMs ? new AbortController() : null
  const timeoutId = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : undefined
  const headers = new Headers(requestInit.headers)
  const isFormData = typeof FormData !== 'undefined' && requestInit.body instanceof FormData
  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  let response: Response

  try {
    response = await fetch(resolveApiUrl(path), {
      ...requestInit,
      headers,
      signal: controller?.signal ?? requestInit.signal,
    })
  } catch (error) {
    if (controller?.signal.aborted) {
      throw new Error(timeoutMessage || '请求超时，请稍后重试。', { cause: error })
    }
    throw error instanceof Error
      ? error
      : new Error('网络请求失败，请稍后重试。', { cause: error })
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId)
    }
  }

  const payload = (await response.json().catch(() => null)) as
    | Partial<ApiResponse<T>> & { detail?: string }
    | null

  if (!response.ok || payload?.code !== 0) {
    const message =
      payload?.message || payload?.detail || `Request failed with ${response.status}`
    throw new Error(response.ok ? message : `HTTP ${response.status}: ${message}`)
  }

  return payload.data as T
}

function postJson<T>(path: string, body: unknown, init: RequestOptions = {}) {
  return request<T>(path, {
    ...init,
    method: 'POST',
    body: JSON.stringify(body),
  })
}

function postForm<T>(path: string, body: FormData, init: RequestOptions = {}) {
  return request<T>(path, {
    ...init,
    method: 'POST',
    body,
  })
}

async function postJsonLineStream<T>(
  path: string,
  body: unknown,
  onDelta: (delta: string) => void,
): Promise<T> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 60000)
  let response: Response

  try {
    response = await fetch(resolveApiUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (error) {
    window.clearTimeout(timeoutId)
    if (controller.signal.aborted) {
      throw new Error('模型流式响应超时，请稍后重试。', { cause: error })
    }
    const apiEndpoint = API_BASE_URL || '当前前端同源 /api 代理'
    throw new Error(`无法连接后端服务（${apiEndpoint}），请确认后端已启动后重试。`, {
      cause: error,
    })
  }

  if (!response.ok) {
    window.clearTimeout(timeoutId)
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null
    throw new Error(payload?.message || payload?.detail || `HTTP ${response.status}`)
  }
  if (!response.body) {
    window.clearTimeout(timeoutId)
    throw new Error('浏览器未收到流式响应。')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed: T | null = null

  function consumeLine(line: string) {
    if (!line.trim()) {
      return
    }
    const event = JSON.parse(line) as
      | { type: 'delta'; delta: string }
      | { type: 'done'; data: T }
      | { type: 'error'; message: string }
    if (event.type === 'delta') {
      onDelta(event.delta)
    } else if (event.type === 'done') {
      completed = event.data
    } else {
      throw new Error(event.message)
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      lines.forEach(consumeLine)
      if (done) {
        if (buffer.trim()) {
          consumeLine(buffer)
        }
        break
      }
    }
  } finally {
    window.clearTimeout(timeoutId)
    reader.releaseLock()
  }

  if (!completed) {
    throw new Error('流式响应未正常完成。')
  }
  return completed
}

export const courseApi = {
  list() {
    return request<CourseSummary[]>('/api/courses')
  },
  knowledgePoints(courseId: string) {
    return request<KnowledgePointSummary[]>(`/api/courses/${courseId}/knowledge-points`)
  },
  knowledgeGraph(courseId: string) {
    return request<KnowledgeGraphResponse>(`/api/courses/${courseId}/knowledge-graph`)
  },
  generateKnowledgeGraph(courseId: string) {
    return postJson<KnowledgeGraphResult>(
      `/api/courses/${courseId}/knowledge-graph/generate`,
      {},
    )
  },
  updateKnowledgeGraph(courseId: string, body: KnowledgeGraphUpdateRequest) {
    return postJson<KnowledgeGraphResult>(
      `/api/courses/${courseId}/knowledge-graph/update`,
      body,
    )
  },
  saveKnowledgeGraph(
    graphId: string,
    body: {
      course_name?: string | null
      graph: NonNullable<KnowledgeGraphUpdateRequest['current_graph']>
    },
  ) {
    return request<KnowledgeGraphResult>(`/api/courses/${graphId}/knowledge-graph`, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
  },
}

export const notebookApi = {
  list(userId: string) {
    const query = buildQuery({ user_id: userId })
    return request<NotebookSummary[]>(`/api/notebooks${query}`)
  },
  detail(notebookId: string, userId: string) {
    const query = buildQuery({ user_id: userId })
    return request<NotebookSummary>(
      `/api/notebooks/${encodeURIComponent(notebookId)}${query}`,
    )
  },
  create(body: { user_id: string; title: string }) {
    return postJson<NotebookSummary>('/api/notebooks', body)
  },
  rename(notebookId: string, params: { user_id: string; title: string }) {
    const query = buildQuery({ user_id: params.user_id })
    return request<NotebookSummary>(
      `/api/notebooks/${encodeURIComponent(notebookId)}${query}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ title: params.title }),
      },
    )
  },
  delete(notebookId: string, userId: string) {
    const query = buildQuery({ user_id: userId })
    return request<{ notebook_id: string; deleted: boolean }>(
      `/api/notebooks/${encodeURIComponent(notebookId)}${query}`,
      { method: 'DELETE' },
    )
  },
}

export const resourceApi = {
  generate(body: ResourceGenerateRequest) {
    return postJson<ResourceGenerateResult>('/api/resource/generate', body)
  },
  list(params: ResourceListParams = {}) {
    const query = buildQuery({
      user_id: params.user_id,
      course_id: params.course_id,
      knowledge_point_id: params.knowledge_point_id,
      type: params.type,
    })

    return request<ResourceListResult>(`/api/resource/list${query}`)
  },
  recommendations(params: ResourceRecommendationParams) {
    const query = buildQuery({
      course_id: params.course_id,
      course_name: params.course_name,
      knowledge_point_id: params.knowledge_point_id,
      query: params.query,
    })

    return request<ResourceRecommendationResult>(`/api/resource/recommendations${query}`, {
      timeoutMs: 12000,
      timeoutMessage: '推荐资源请求超时，请稍后重试。',
    })
  },
  detail(resourceId: string) {
    return request<LearningResourceDetail>(`/api/resource/${encodeURIComponent(resourceId)}`)
  },
  delete(resourceId: string) {
    return request<{ deleted: boolean }>(`/api/resource/${encodeURIComponent(resourceId)}`, {
      method: 'DELETE',
    })
  },
}

export const taskApi = {
  detail(taskId: string) {
    return request<AgentTask>(`/api/task/${encodeURIComponent(taskId)}`)
  },
  events(taskId: string) {
    return request<{ task_id: string; events: TaskEvent[] }>(
      `/api/task/${encodeURIComponent(taskId)}/events`,
    )
  },
}

export const tutorApi = {
  ask(body: TutorAskRequest) {
    return postJson<TutorAskResult>('/api/tutor/ask', body, {
      timeoutMs: 30000,
      timeoutMessage: '模型响应超时，请稍后重试。',
    })
  },
  async preview(file: File) {
    const body = new FormData()
    body.set('file', file)
    const result = await postForm<TutorPreviewResult>('/api/tutor/preview', body, {
      timeoutMs: 65000,
      timeoutMessage: '文件预览生成超时，请稍后重试。',
    })

    return {
      ...result,
      preview_url: resolveApiUrl(result.preview_url),
    }
  },
  codeReview(body: CodeReviewRequest) {
    return postJson<CodeReviewResult>('/api/tutor/code-review', body)
  },
}

export const classroomApi = {
  studio(params: { user_id: string; course_id: string; notebook_id?: string }) {
    const query = buildQuery({
      user_id: params.user_id,
      course_id: params.course_id,
      notebook_id: params.notebook_id,
    })
    return request<ClassroomStudioListResult>(`/api/classroom/studio${query}`)
  },
  profile(params: { user_id: string; course_id: string; notebook_id?: string }) {
    const query = buildQuery({
      user_id: params.user_id,
      course_id: params.course_id,
      notebook_id: params.notebook_id,
    })
    return request<UserProfileResult>(`/api/classroom/profile${query}`, {
      timeoutMs: 45000,
      timeoutMessage: '用户画像生成超时，请稍后重试。',
      cache: 'no-store',
    })
  },
  generateProfile(body: UserProfileGenerateRequest) {
    return postJson<UserProfileResult>('/api/classroom/profile/generate', body, {
      timeoutMs: 45000,
      timeoutMessage: '用户画像生成超时，请稍后重试。',
      cache: 'no-store',
    })
  },
  ask(body: TutorAskRequest) {
    return postJson<TutorAskResult>('/api/classroom/ask', body)
  },
  askStream(body: TutorAskRequest, onDelta: (delta: string) => void) {
    return postJsonLineStream<TutorAskResult>('/api/classroom/ask/stream', body, onDelta)
  },
  deleteHistory(params: {
    user_id: string
    course_id?: string
    notebook_id?: string
    visit_id?: string
    keepalive?: boolean
  }) {
    const query = buildQuery({
      user_id: params.user_id,
      course_id: params.course_id,
      notebook_id: params.notebook_id,
      visit_id: params.visit_id,
    })
    return request<{ deleted: boolean; deleted_sessions: number }>(
      `/api/classroom/history${query}`,
      {
        method: 'DELETE',
        keepalive: params.keepalive,
      },
    )
  },
  generate(body: ClassroomGenerateRequest) {
    return postJson<ClassroomGenerateResult>('/api/classroom/generate', body)
  },
  detail(sessionId: string) {
    return request<ClassroomDetail>(`/api/classroom/${encodeURIComponent(sessionId)}`)
  },
  generateQuiz(body: ClassroomQuizGenerateRequest) {
    return postJson<ClassroomQuizGenerateResult>('/api/classroom/quiz/generate', body)
  },
  recordQuizPractice(body: QuizPracticeRecordRequest) {
    return postJson<QuizPracticeRecord>('/api/classroom/quiz/practice', body)
  },
  generateFlashcards(body: ClassroomFlashcardsGenerateRequest) {
    return postJson<ClassroomFlashcardsGenerateResult>(
      '/api/classroom/flashcards/generate',
      body,
    )
  },
  recordFlashcardPractice(body: FlashcardPracticeRecordRequest) {
    return postJson<FlashcardPracticeRecord>('/api/classroom/flashcards/practice', body)
  },
  resetFlashcardPractice(params: { flashcard_set_id: string; user_id: string }) {
    return postJson<{ cleared: boolean; flashcard_set_id: string }>(
      `/api/classroom/flashcards/${encodeURIComponent(params.flashcard_set_id)}/practice/reset`,
      { user_id: params.user_id },
    )
  },
  deleteQuiz(params: { quiz_id: string; user_id: string }) {
    const query = buildQuery({ user_id: params.user_id })
    return request<{ deleted: boolean; quiz_id: string }>(
      `/api/classroom/quiz/${encodeURIComponent(params.quiz_id)}${query}`,
      { method: 'DELETE' },
    )
  },
  deleteFlashcards(params: { flashcard_set_id: string; user_id: string }) {
    const query = buildQuery({ user_id: params.user_id })
    return request<{ deleted: boolean; flashcard_set_id: string }>(
      `/api/classroom/flashcards/${encodeURIComponent(params.flashcard_set_id)}${query}`,
      { method: 'DELETE' },
    )
  },
}

export const ragApi = {
  documents(params: { user_id?: string; course_id?: string; notebook_id?: string } = {}) {
    const query = buildQuery({
      user_id: params.user_id,
      course_id: params.course_id,
      notebook_id: params.notebook_id,
    })
    return request<RAGDocumentListResult>(`/api/rag/documents${query}`, {
      timeoutMs: 10000,
      timeoutMessage: '读取来源超时，请稍后重试。',
      cache: 'no-store',
    })
  },
  uploadFile(params: { user_id: string; course_id: string; notebook_id?: string; file: File }) {
    const formData = new FormData()
    formData.set('user_id', params.user_id)
    formData.set('course_id', params.course_id)
    if (params.notebook_id) {
      formData.set('notebook_id', params.notebook_id)
    }
    formData.set('file', params.file)

    return request<RAGUploadResult>('/api/rag/upload-file', {
      method: 'POST',
      body: formData,
    })
  },
  deleteDocument(documentId: string) {
    return request<{ deleted: boolean; document_id: string }>(
      `/api/rag/documents/${encodeURIComponent(documentId)}`,
      { method: 'DELETE' },
    )
  },
  renameDocument(documentId: string, sourceTitle: string) {
    return request<RAGDocumentSummary>(
      `/api/rag/documents/${encodeURIComponent(documentId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ source_title: sourceTitle }),
      },
    )
  },
}
