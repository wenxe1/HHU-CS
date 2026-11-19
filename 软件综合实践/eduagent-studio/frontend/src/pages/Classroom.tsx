import {
  useEffect,
  useCallback,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  type MouseEvent,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import ReactMarkdown from 'react-markdown'
import {
  ArrowLeft,
  Check,
  ChevronLeft,
  ChevronRight,
  Clipboard,
  FileText,
  Loader2,
  Minimize2,
  MoreHorizontal,
  Plus,
  RotateCcw,
  Send,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { useOutletContext } from 'react-router'
import remarkGfm from 'remark-gfm'
import {
  classroomApi,
  ragApi,
  type ClassroomFlashcardsGenerateResult,
  type ClassroomQuizGenerateResult,
  type FlashcardItem,
  type FlashcardPracticeRecord,
  type FlashcardPracticeResult,
  type NotebookSummary,
  type QuizQuestion,
  type RAGDocumentSummary,
} from '../lib/api'
import { getActiveUserId } from '../lib/auth'
import {
  useNotebookSessionState,
  useNotebookVisitId,
} from '../layouts/NotebookSessionContext'

const SOURCE_FILE_ACCEPT = [
  '.pdf',
  '.docx',
  '.md',
  '.markdown',
  '.txt',
  '.png',
  '.jpg',
  '.jpeg',
  '.webp',
  '.gif',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
].join(',')

const PASTED_TEXT_SOURCE_NAME = '粘贴的文字'
const PASTED_TEXT_UPLOAD_FILENAME = `${PASTED_TEXT_SOURCE_NAME}.txt`
const MAX_PENDING_STUDIO_GENERATIONS = 5
const STUDIO_GENERATION_RETRY_LIMIT = 5
const STUDIO_GENERATION_RETRY_DELAY_MS = 1200

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  guidanceSteps?: string[]
}

type StudioMode = 'empty' | 'quiz' | 'flashcards'
type SourceDialogMode = 'files' | 'text'
type StudioGenerationKind = 'quiz' | 'flashcards' | null
type PendingStudioGeneration = {
  id: string
  kind: Exclude<StudioGenerationKind, null>
  selectedCount: number
}
type FlashcardReviewScope = 'all' | 'incorrect'
type QuizReviewScope = 'all' | 'incorrect'
type ClassroomIconProps = {
  size?: number
}

type GoogleSymbolName =
  | 'article'
  | 'cards_star'
  | 'docs'
  | 'drive_pdf'
  | 'image'
  | 'quiz'

type PracticeStats = {
  correct: number
  incorrect: number
  skipped: number
  total: number
  isComplete: boolean
}

function toErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '请求失败'
}

function formatDate(value: string) {
  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) {
    return '刚刚'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(timestamp)
}

function formatArtifactTime(value?: string) {
  if (!value) {
    return '刚刚'
  }
  return formatDate(value)
}

function formatNotebookDate(date: Date) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
}

function createFlashcardAttemptId() {
  return globalThis.crypto?.randomUUID?.() ?? `flashcard-attempt-${Date.now()}-${Math.random()}`
}

function practiceRecordMap(records: FlashcardPracticeRecord[]) {
  return new Map(records.map((record) => [record.card_id, record]))
}

function flashcardStats(cards: FlashcardItem[], records: FlashcardPracticeRecord[]) {
  const cardIds = new Set(cards.map((card) => card.card_id))
  const scoped = records.filter((record) => cardIds.has(record.card_id))
  const correct = scoped.filter((record) => record.result === 'correct').length
  const incorrect = scoped.filter((record) => record.result === 'incorrect').length
  const answered = new Set(scoped.map((record) => record.card_id)).size
  return {
    correct,
    incorrect,
    answered,
    skipped: Math.max(0, cards.length - answered),
    total: cards.length,
    isComplete: cards.length > 0 && answered >= cards.length,
  }
}

function quizStats(
  questions: QuizQuestion[],
  selectedAnswers: Record<string, string>,
  revealedQuestions: Set<string>,
) {
  const answeredQuestions = questions.filter((question) =>
    revealedQuestions.has(question.question_id),
  )
  const correct = answeredQuestions.filter(
    (question) => selectedAnswers[question.question_id] === question.answer,
  ).length
  const incorrect = answeredQuestions.length - correct
  return {
    correct,
    incorrect,
    answered: answeredQuestions.length,
    skipped: Math.max(0, questions.length - answeredQuestions.length),
    total: questions.length,
    isComplete: questions.length > 0 && answeredQuestions.length >= questions.length,
  }
}

function optionLetter(index: number) {
  return String.fromCharCode(65 + index)
}

function displayQuizOption(option: string) {
  return option.replace(/^\s*[A-ZＡ-Ｚ]\s*[.．、]\s*/u, '').trim() || option
}

function optionExplanation(question: QuizQuestion, option: string) {
  return (
    question.option_explanations?.[option] ||
    (option === question.answer
      ? question.explanation
      : '该选项与来源材料中的关键信息不完全一致。')
  )
}

function buildFlashcardExplainPrompt(card: FlashcardItem) {
  return [
    '我正在复习基于来源材料制作的抽认卡，并想深入了解其中一张卡片。',
    '',
    `这张卡片的正面显示：${card.front}`,
    `背面的答案显示：${card.back}`,
    '',
    '请详细讲讲这个主题。',
  ].join('\n')
}

function buildQuizMistakePrompt(question: QuizQuestion, selectedAnswer: string) {
  return [
    `我在做这份材料的测验时遇到了这个问题：${question.stem}`,
    '',
    `我选择的答案是：${selectedAnswer}`,
    '',
    `选错了。正确的答案是${question.answer}`,
    '',
    '请解释一下我选择的答案哪里错了。',
  ].join('\n')
}

function fileKind(filename: string) {
  const lower = filename.toLowerCase()
  if (
    lower.endsWith('.png') ||
    lower.endsWith('.jpg') ||
    lower.endsWith('.jpeg') ||
    lower.endsWith('.webp') ||
    lower.endsWith('.gif')
  ) {
    return 'IMAGE'
  }
  if (lower.endsWith('.pdf')) {
    return 'PDF'
  }
  if (lower.endsWith('.docx')) {
    return 'DOCX'
  }
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) {
    return 'MD'
  }
  if (lower.endsWith('.txt')) {
    return 'TXT'
  }
  return 'DOC'
}

function isSourceReady(document: RAGDocumentSummary) {
  return (document.upload_status ?? 'success') === 'success'
}

function isSourceProcessing(document: RAGDocumentSummary) {
  return document.upload_status === 'processing'
}

function isSourceFailed(document: RAGDocumentSummary) {
  return document.upload_status === 'failed'
}

function isPastedTextSource(document: RAGDocumentSummary) {
  return (
    document.filename === PASTED_TEXT_UPLOAD_FILENAME ||
    document.source_title === PASTED_TEXT_UPLOAD_FILENAME
  )
}

function normalizeSourceDisplayTitle(title: string) {
  return title === PASTED_TEXT_UPLOAD_FILENAME ? PASTED_TEXT_SOURCE_NAME : title
}

function createStudioGenerationId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
}

function waitForStudioRetry(attemptIndex: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, STUDIO_GENERATION_RETRY_DELAY_MS * attemptIndex)
  })
}

async function retryStudioGeneration<T>(request: () => Promise<T>) {
  for (let attempt = 1; attempt <= STUDIO_GENERATION_RETRY_LIMIT; attempt += 1) {
    try {
      return await request()
    } catch {
      if (attempt === STUDIO_GENERATION_RETRY_LIMIT) {
        throw new Error('studio generation failed')
      }
      await waitForStudioRetry(attempt)
    }
  }
  throw new Error('studio generation failed')
}

function sourceDisplayName(document: RAGDocumentSummary) {
  if (isPastedTextSource(document)) {
    return PASTED_TEXT_SOURCE_NAME
  }
  return normalizeSourceDisplayTitle(document.source_title || document.filename)
}

function createPendingSource(
  file: File,
  userId: string,
  courseId: string,
  notebookId: string,
): RAGDocumentSummary {
  const documentId = `pending-${Date.now()}-${Math.random().toString(36).slice(2)}`
  const now = new Date().toISOString()
  const filename = file.name || '未命名来源'
  const sourceTitle = filename === PASTED_TEXT_UPLOAD_FILENAME ? PASTED_TEXT_SOURCE_NAME : filename

  return {
    document_id: documentId,
    source_id: documentId,
    user_id: userId,
    course_id: courseId,
    notebook_id: notebookId,
    filename,
    source_title: sourceTitle,
    source_content: '',
    content_type: file.type || 'application/octet-stream',
    source_type: fileKind(filename).toLowerCase(),
    upload_status: 'processing',
    processing_error: null,
    chunk_count: 0,
    metadata: { local: 'true' },
    created_at: now,
    updated_at: now,
  }
}

function CollapsePanelIcon({ size = 20 }: ClassroomIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      aria-hidden="true"
    >
      <rect x="4" y="3" width="16" height="18" rx="1" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M9 4v16" stroke="currentColor" strokeWidth="2" strokeLinecap="square" />
    </svg>
  )
}

function GoogleSymbolIcon({
  name,
  size = 24,
}: ClassroomIconProps & { name: GoogleSymbolName }) {
  return (
    <span
      className="google-symbol-icon"
      style={{ fontSize: size, width: size, height: size }}
      aria-hidden="true"
    >
      {name}
    </span>
  )
}

function QuizToolIcon({ size = 24 }: ClassroomIconProps) {
  return <GoogleSymbolIcon name="quiz" size={size} />
}

function FlashcardToolIcon({ size = 24 }: ClassroomIconProps) {
  return <GoogleSymbolIcon name="cards_star" size={size} />
}

function FloatingActionMenu({
  anchorElement,
  className,
  menuWidth = 168,
  menuHeight = 96,
  onClose,
  children,
}: {
  anchorElement: HTMLElement | null
  className?: string
  menuWidth?: number
  menuHeight?: number
  onClose: () => void
  children: ReactNode
}) {
  const menuRef = useRef<HTMLDivElement | null>(null)
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)

  useEffect(() => {
    if (!anchorElement) {
      return
    }
    const anchor = anchorElement

    function updatePosition() {
      const rect = anchor.getBoundingClientRect()
      const belowTop = rect.bottom + 6
      const aboveTop = rect.top - menuHeight - 6
      const top =
        belowTop + menuHeight <= window.innerHeight - 8
          ? belowTop
          : Math.max(8, aboveTop)
      const left = Math.min(
        Math.max(8, rect.right - menuWidth),
        Math.max(8, window.innerWidth - menuWidth - 8),
      )
      setPosition({ top, left })
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node
      if (anchor.contains(target) || menuRef.current?.contains(target)) {
        return
      }
      onClose()
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    updatePosition()
    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [anchorElement, menuHeight, menuWidth, onClose])

  if (!anchorElement || !position) {
    return null
  }

  return createPortal(
    <div
      ref={menuRef}
      className={`classroom-action-menu floating-action-menu${className ? ` ${className}` : ''}`}
      role="menu"
      style={{
        top: position.top,
        left: position.left,
        width: menuWidth,
      }}
    >
      {children}
    </div>,
    document.body,
  )
}

function SourcePanel({
  documents,
  selectedIds,
  isLoading,
  isUploading,
  isCollapsed,
  onAddSource,
  onToggle,
  onToggleAll,
  onDeleteSource,
  onToggleCollapse,
}: {
  documents: RAGDocumentSummary[]
  selectedIds: Set<string>
  isLoading: boolean
  isUploading: boolean
  isCollapsed: boolean
  onAddSource: () => void
  onToggle: (documentId: string) => void
  onToggleAll: () => void
  onDeleteSource: (documentId: string) => void
  onToggleCollapse: () => void
}) {
  const selectableDocuments = documents.filter(isSourceReady)
  const allSelected =
    selectableDocuments.length > 0 &&
    selectableDocuments.every((document) => selectedIds.has(document.document_id))

  return (
    <section className={`interactive-panel source-panel${isCollapsed ? ' is-collapsed' : ''}`} aria-label="资料来源区">
      <div className="interactive-panel-head">
        <h2>来源</h2>
        <button
          className="icon-quiet-button panel-collapse-button"
          type="button"
          aria-label={isCollapsed ? '展开来源' : '折叠来源'}
          aria-expanded={!isCollapsed}
          onClick={onToggleCollapse}
        >
          <CollapsePanelIcon size={20} />
        </button>
      </div>

      <div className="panel-transition-body">
        <div
          className={`panel-view panel-expanded-view${isCollapsed ? ' is-hidden' : ''}`}
          aria-hidden={isCollapsed}
        >
          <SourceUploader
            isUploading={isUploading}
            onAddSource={onAddSource}
          />

          {documents.length > 0 ? (
            <div className="source-list-head">
              <button type="button" onClick={onToggleAll}>
                <span>全选</span>
                <span className={`source-check ${allSelected ? 'is-checked' : ''}`}>
                  {allSelected ? <Check size={14} strokeWidth={2.3} /> : null}
                </span>
              </button>
            </div>
          ) : null}

          <SourceList
            documents={documents}
            selectedIds={selectedIds}
            isLoading={isLoading}
            onToggle={onToggle}
            onDeleteSource={onDeleteSource}
          />
        </div>

        <div
          className={`panel-view panel-collapsed-view${isCollapsed ? '' : ' is-hidden'}`}
          aria-hidden={!isCollapsed}
        >
          <SourceCollapsedRail
            documents={documents}
            selectedIds={selectedIds}
            isLoading={isLoading}
            isUploading={isUploading}
            onAddSource={onAddSource}
            onToggle={onToggle}
          />
        </div>
      </div>
    </section>
  )
}

function SourceCollapsedRail({
  documents,
  selectedIds,
  isLoading,
  isUploading,
  onAddSource,
  onToggle,
}: {
  documents: RAGDocumentSummary[]
  selectedIds: Set<string>
  isLoading: boolean
  isUploading: boolean
  onAddSource: () => void
  onToggle: (documentId: string) => void
}) {
  return (
    <div className="source-collapsed-rail" aria-label="折叠后的来源">
      <button
        className="source-rail-add-button"
        type="button"
        aria-label="添加来源"
        onClick={onAddSource}
        disabled={isUploading}
      >
        {isUploading ? <Loader2 className="source-status-spin" size={20} strokeWidth={1.9} /> : <Plus size={22} strokeWidth={2} />}
      </button>

      {isLoading ? (
        <span className="source-rail-loading" aria-label="正在读取来源">
          <Loader2 className="source-status-spin" size={18} strokeWidth={1.9} />
        </span>
      ) : null}

      {!isLoading && documents.length > 0 ? (
        <div className="source-rail-file-list">
          {documents.map((document) => {
            const displayName = sourceDisplayName(document)
            const isSelected = selectedIds.has(document.document_id)
            const isProcessing = isSourceProcessing(document)
            const isFailed = isSourceFailed(document)
            return (
              <button
                className={`source-rail-file-button${isSelected ? ' is-selected' : ''}${
                  isProcessing ? ' is-processing' : ''
                }${isFailed ? ' is-failed' : ''}`}
                type="button"
                aria-label={displayName}
                title={displayName}
                onClick={() => onToggle(document.document_id)}
                disabled={isProcessing || isFailed}
                key={document.document_id}
              >
                {isProcessing ? (
                  <Loader2 className="source-status-spin" size={16} strokeWidth={2} />
                ) : (
                  <CompactSourceIcon filename={document.filename} />
                )}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

function SourceUploader({
  isUploading,
  onAddSource,
}: {
  isUploading: boolean
  onAddSource: () => void
}) {
  return (
    <div className="source-uploader">
      <button className="add-source-button" type="button" onClick={onAddSource} disabled={isUploading}>
        {isUploading ? <Loader2 className="source-status-spin" size={18} strokeWidth={1.9} /> : <Plus size={18} strokeWidth={2} />}
        添加来源
      </button>
    </div>
  )
}

function SourceDialog({
  isOpen,
  mode,
  isUploading,
  pastedText,
  onClose,
  onModeChange,
  onPastedTextChange,
  onUploadClick,
  onFilesDrop,
  onSubmitText,
}: {
  isOpen: boolean
  mode: SourceDialogMode
  isUploading: boolean
  pastedText: string
  onClose: () => void
  onModeChange: (mode: SourceDialogMode) => void
  onPastedTextChange: (value: string) => void
  onUploadClick: () => void
  onFilesDrop: (files: File[]) => void
  onSubmitText: () => void
}) {
  const [isDragging, setIsDragging] = useState(false)
  const hasPastedText = pastedText.trim().length > 0

  useEffect(() => {
    if (!isOpen) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  function handleBackdropMouseDown(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    if (!isUploading) {
      setIsDragging(true)
    }
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setIsDragging(false)
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    if (isUploading) {
      return
    }
    onFilesDrop(Array.from(event.dataTransfer.files))
  }

  if (!isOpen) {
    return null
  }

  return (
    <div className="source-dialog-backdrop" role="presentation" onMouseDown={handleBackdropMouseDown}>
      <section
        className={`source-dialog is-${mode}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-dialog-title"
      >
        {mode === 'files' ? (
          <div className="source-dialog-content" key="files">
            <button className="source-dialog-close" type="button" aria-label="关闭添加来源窗口" onClick={onClose}>
              <X size={21} strokeWidth={2} />
            </button>
            <h2 id="source-dialog-title">根据以下内容生成测验和闪卡</h2>
            <div
              className={`source-drop-zone${isDragging ? ' is-dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <span className="source-drop-icon" aria-hidden="true">
                {isUploading ? <Loader2 className="source-status-spin" size={28} strokeWidth={1.9} /> : <Upload size={28} strokeWidth={1.9} />}
              </span>
              <strong>{isUploading ? '正在上传来源' : '或拖放文件'}</strong>
              <p>支持图片、PDF、Word 文档和纯文字文件</p>
              <div className="source-dialog-action-row">
                <button className="source-dialog-pill-button" type="button" onClick={onUploadClick} disabled={isUploading}>
                  <Upload size={17} strokeWidth={2} />
                  上传文件
                </button>
                <button
                  className="source-dialog-pill-button"
                  type="button"
                  onClick={() => onModeChange('text')}
                  disabled={isUploading}
                >
                  <Clipboard size={17} strokeWidth={2} />
                  复制的文字
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="source-dialog-content" key="text">
            <div className="source-text-head">
              <button className="source-dialog-icon-button" type="button" aria-label="返回添加来源" onClick={() => onModeChange('files')}>
                <ArrowLeft size={22} strokeWidth={2} />
              </button>
              <h2 id="source-dialog-title">粘贴复制的文字</h2>
              <button className="source-dialog-icon-button" type="button" aria-label="关闭添加来源窗口" onClick={onClose}>
                <X size={22} strokeWidth={2} />
              </button>
            </div>
            <p className="source-text-copy">在下方粘贴文字，即可将其作为纯文字来源上传。</p>
            <textarea
              className="source-textarea"
              value={pastedText}
              onChange={(event) => onPastedTextChange(event.target.value)}
              placeholder="在此处粘贴文字"
              autoFocus
            />
            <div className="source-text-footer">
              <button
                className="source-insert-button"
                type="button"
                onClick={onSubmitText}
                disabled={isUploading || !hasPastedText}
              >
                {isUploading ? <Loader2 className="source-status-spin" size={17} strokeWidth={1.9} /> : null}
                插入
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

function SourceList({
  documents,
  selectedIds,
  isLoading,
  onToggle,
  onDeleteSource,
}: {
  documents: RAGDocumentSummary[]
  selectedIds: Set<string>
  isLoading: boolean
  onToggle: (documentId: string) => void
  onDeleteSource: (documentId: string) => void
}) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [menuAnchorElement, setMenuAnchorElement] = useState<HTMLButtonElement | null>(null)
  const activeMenuDocument = openMenuId
    ? documents.find((document) => document.document_id === openMenuId)
    : null

  function closeMenu() {
    setOpenMenuId(null)
    setMenuAnchorElement(null)
  }

  if (isLoading && documents.length === 0) {
    return (
      <div className="source-empty-state">
        <Loader2 className="source-status-spin" size={22} strokeWidth={1.9} />
        <strong>正在读取来源</strong>
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="source-empty-state">
        <FileText size={28} strokeWidth={1.8} />
        <strong>已保存的来源将显示在此处</strong>
        <p>点击上方的添加来源即可添加图片、PDF、文档或文本</p>
      </div>
    )
  }

  return (
    <>
      <div className="source-list" aria-label="资料来源列表">
        {documents.map((document) => {
          const displayName = sourceDisplayName(document)
          const isSelected = selectedIds.has(document.document_id)
          const isProcessing = isSourceProcessing(document)
          const isFailed = isSourceFailed(document)
          const isSelectable = isSourceReady(document)
          return (
            <article
              className={`source-item ${isSelected ? 'is-selected' : ''}${
                isProcessing ? ' is-processing' : ''
              }${isFailed ? ' is-failed' : ''}`}
              key={document.document_id}
            >
              <FileTypeIcon filename={document.filename} />
              <button
                type="button"
                className="source-main"
                onClick={() => onToggle(document.document_id)}
                disabled={!isSelectable}
              >
                <strong>{displayName}</strong>
              </button>
              {isProcessing ? (
                <span className="source-status-indicator" aria-label="正在处理来源">
                  <Loader2 className="source-status-spin" size={20} strokeWidth={2} />
                </span>
              ) : isFailed ? (
                <span className="source-status-indicator is-failed" aria-label="来源上传失败">
                  <X size={18} strokeWidth={2} />
                </span>
              ) : (
                <>
                  <button
                    className="source-more-button"
                    type="button"
                    aria-label={`${displayName} 更多操作`}
                    aria-haspopup="menu"
                    aria-expanded={openMenuId === document.document_id}
                    onClick={(event) => {
                      const isOpen = openMenuId === document.document_id
                      setOpenMenuId(isOpen ? null : document.document_id)
                      setMenuAnchorElement(isOpen ? null : event.currentTarget)
                    }}
                  >
                    <MoreHorizontal size={16} strokeWidth={2} />
                  </button>
                  <label className="source-checkbox" aria-label={`选择 ${displayName}`}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggle(document.document_id)}
                    />
                    <span>{isSelected ? <Check size={14} strokeWidth={2.3} /> : null}</span>
                  </label>
                </>
              )}
            </article>
          )
        })}
      </div>
      {activeMenuDocument ? (
        <SourceActionMenu
          anchorElement={menuAnchorElement}
          onClose={closeMenu}
          onDelete={() => {
            closeMenu()
            onDeleteSource(activeMenuDocument.document_id)
          }}
        />
      ) : null}
    </>
  )
}

function SourceActionMenu({
  anchorElement,
  onClose,
  onDelete,
}: {
  anchorElement: HTMLElement | null
  onClose: () => void
  onDelete: () => void
}) {
  return (
    <FloatingActionMenu
      anchorElement={anchorElement}
      className="studio-artifact-action-menu"
      menuWidth={168}
      menuHeight={44}
      onClose={onClose}
    >
      <button type="button" role="menuitem" onClick={onDelete}>
        <Trash2 size={17} strokeWidth={1.9} />
        移除来源
      </button>
    </FloatingActionMenu>
  )
}

function FileTypeIcon({ filename }: { filename: string }) {
  const kind = fileKind(filename)
  const iconName: GoogleSymbolName =
    kind === 'IMAGE'
      ? 'image'
      : kind === 'PDF'
        ? 'drive_pdf'
        : kind === 'DOCX'
          ? 'article'
          : 'docs'

  return (
    <span className={`source-file-icon tone-${kind.toLowerCase()}`}>
      <GoogleSymbolIcon name={iconName} size={24} />
    </span>
  )
}

function CompactSourceIcon({ filename }: { filename: string }) {
  const kind = fileKind(filename)
  const iconName: GoogleSymbolName =
    kind === 'IMAGE'
      ? 'image'
      : kind === 'PDF'
        ? 'drive_pdf'
        : kind === 'DOCX'
          ? 'article'
          : 'docs'

  return (
    <span className={`source-rail-file-icon tone-${kind.toLowerCase()}`}>
      <GoogleSymbolIcon name={iconName} size={20} />
    </span>
  )
}

function ChatPanel({
  messages,
  draft,
  selectedCount,
  sourceCount,
  notebookTitle,
  isAsking,
  errorMessage,
  onDraftChange,
  onSubmit,
  onDeleteMessages,
}: {
  messages: ChatMessage[]
  draft: string
  selectedCount: number
  sourceCount: number
  notebookTitle: string
  isAsking: boolean
  errorMessage: string
  onDraftChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onDeleteMessages: () => void
}) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const chatBodyRef = useRef<HTMLDivElement | null>(null)

  function handleDeleteMessages() {
    setIsMenuOpen(false)
    onDeleteMessages()
  }

  useEffect(() => {
    const chatBody = chatBodyRef.current
    if (!chatBody) {
      return
    }
    window.requestAnimationFrame(() => {
      chatBody.scrollTop = chatBody.scrollHeight
    })
  }, [messages, isAsking])

  return (
    <section className="interactive-panel chat-panel" aria-label="AI 对话区">
      <div className="interactive-panel-head">
        <h2>对话</h2>
        <div className="chat-head-actions">
          <button
            className="icon-quiet-button"
            type="button"
            aria-label="更多对话操作"
            aria-haspopup="menu"
            aria-expanded={isMenuOpen}
            onClick={() => setIsMenuOpen((current) => !current)}
          >
            <MoreHorizontal size={18} strokeWidth={2} />
          </button>
          {isMenuOpen ? (
            <div className="classroom-action-menu chat-action-menu" role="menu">
              <button type="button" role="menuitem" onClick={handleDeleteMessages}>
                <Trash2 size={17} strokeWidth={1.9} />
                删除对话记录
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <div className="chat-body" ref={chatBodyRef}>
        {messages.length === 0 ? (
          <ChatWelcome
            title={notebookTitle}
            sourceCount={sourceCount}
          />
        ) : (
          <ChatMessageList messages={messages} isAsking={isAsking} />
        )}
      </div>

      {errorMessage.length > 0 ? <p className="interactive-error">{errorMessage}</p> : null}

      <ChatInput
        draft={draft}
        selectedCount={selectedCount}
        isAsking={isAsking}
        onDraftChange={onDraftChange}
        onSubmit={onSubmit}
      />
    </section>
  )
}
function ChatWelcome({
  title,
  sourceCount,
}: {
  title: string
  sourceCount: number
}) {
  return (
    <div className="chat-welcome">
      <div className="chat-welcome-copy">
        <span className="chat-empty-hero-icon" aria-hidden="true">📖</span>
        <h3>{title}</h3>
        <p>{sourceCount} 个来源 · {formatNotebookDate(new Date())}</p>
      </div>
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}

function AIBreathingIndicator() {
  return (
    <span className="ai-breathing-indicator" role="status" aria-label="EduAgent 正在回复">
      <i />
      <i />
      <i />
      <i />
    </span>
  )
}

function ChatMessageList({ messages, isAsking }: { messages: ChatMessage[]; isAsking: boolean }) {
  const hasPendingAssistant = messages.at(-1)?.role === 'assistant'

  return (
    <div className="chat-message-list" aria-live="polite">
      {messages.map((message, index) => (
        <article className={`chat-message ${message.role}`} key={message.id}>
          {message.role === 'assistant' ? (
            <span className="chat-message-author">EduAgent</span>
          ) : null}
          {message.role === 'assistant' ? (
            message.content.trim().length > 0 ? (
              <MarkdownContent content={message.content} />
            ) : (
              isAsking && index === messages.length - 1 ? <AIBreathingIndicator /> : null
            )
          ) : (
            <p>{message.content}</p>
          )}
          {message.guidanceSteps?.length ? (
            <ol>
              {message.guidanceSteps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          ) : null}
        </article>
      ))}
      {isAsking && !hasPendingAssistant ? (
        <article className="chat-message assistant is-loading">
          <span className="chat-message-author">EduAgent</span>
          <AIBreathingIndicator />
        </article>
      ) : null}
    </div>
  )
}

function ChatInput({
  draft,
  selectedCount,
  isAsking,
  onDraftChange,
  onSubmit,
}: {
  draft: string
  selectedCount: number
  isAsking: boolean
  onDraftChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <form className="classroom-chat-input" onSubmit={onSubmit}>
      <input
        value={draft}
        onChange={(event) => onDraftChange(event.target.value)}
        placeholder="开始输入..."
        aria-label="输入问题"
      />
      <span>{selectedCount} 个来源</span>
      <button type="submit" aria-label="发送问题" disabled={isAsking}>
        {isAsking ? <Loader2 size={18} strokeWidth={1.9} /> : <Send size={18} strokeWidth={2} />}
      </button>
    </form>
  )
}

function StudioPanel({
  mode,
  selectedCount,
  quiz,
  flashcards,
  quizzes,
  flashcardSets,
  documents,
  practiceRecords,
  pendingGenerations,
  isGenerating,
  canStartGeneration,
  isCollapsed,
  errorMessage,
  revealedQuestions,
  selectedAnswers,
  activeQuizQuestionIndex,
  quizStudyQuestionIds,
  activeCardIndex,
  isCardFlipped,
  studyCardIds,
  cardFeedback,
  isSourceListOpen,
  isQuizRestartMenuOpen,
  isRestartMenuOpen,
  onGenerateQuiz,
  onGenerateFlashcards,
  onOpenQuiz,
  onOpenFlashcards,
  onViewQuizSources,
  onViewFlashcardSources,
  onDeleteQuiz,
  onDeleteFlashcards,
  onCloseStudioApp,
  onSelectAnswer,
  onRevealQuestion,
  onRecordQuizPractice,
  onNextQuizQuestion,
  onExplainQuizMistake,
  onToggleQuizRestartMenu,
  onRestartQuiz,
  onPreviousCard,
  onNextCard,
  onFlipCard,
  onMarkFlashcard,
  onExplainFlashcard,
  onToggleSourceList,
  onToggleRestartMenu,
  onRestartFlashcards,
  onToggleCollapse,
}: {
  mode: StudioMode
  selectedCount: number
  quiz: ClassroomQuizGenerateResult | null
  flashcards: ClassroomFlashcardsGenerateResult | null
  quizzes: ClassroomQuizGenerateResult[]
  flashcardSets: ClassroomFlashcardsGenerateResult[]
  documents: RAGDocumentSummary[]
  practiceRecords: FlashcardPracticeRecord[]
  pendingGenerations: PendingStudioGeneration[]
  isGenerating: boolean
  canStartGeneration: boolean
  isCollapsed: boolean
  errorMessage: string
  revealedQuestions: Set<string>
  selectedAnswers: Record<string, string>
  activeQuizQuestionIndex: number
  quizStudyQuestionIds: string[]
  activeCardIndex: number
  isCardFlipped: boolean
  studyCardIds: string[]
  cardFeedback: FlashcardPracticeResult | null
  isSourceListOpen: boolean
  isQuizRestartMenuOpen: boolean
  isRestartMenuOpen: boolean
  onGenerateQuiz: () => void
  onGenerateFlashcards: () => void
  onOpenQuiz: (quiz: ClassroomQuizGenerateResult) => void
  onOpenFlashcards: (flashcardSet: ClassroomFlashcardsGenerateResult) => void
  onViewQuizSources: (quiz: ClassroomQuizGenerateResult) => void
  onViewFlashcardSources: (flashcardSet: ClassroomFlashcardsGenerateResult) => void
  onDeleteQuiz: (quizId: string) => void
  onDeleteFlashcards: (flashcardSetId: string) => void
  onCloseStudioApp: () => void
  onSelectAnswer: (questionId: string, answer: string) => void
  onRevealQuestion: (questionId: string) => void
  onRecordQuizPractice: (question: QuizQuestion, selectedAnswer: string) => void
  onNextQuizQuestion: () => void
  onExplainQuizMistake: (question: QuizQuestion) => void
  onToggleQuizRestartMenu: () => void
  onRestartQuiz: (scope: QuizReviewScope) => void
  onPreviousCard: () => void
  onNextCard: () => void
  onFlipCard: () => void
  onMarkFlashcard: (result: FlashcardPracticeResult) => void
  onExplainFlashcard: (card: FlashcardItem) => void
  onToggleSourceList: () => void
  onToggleRestartMenu: () => void
  onRestartFlashcards: (scope: FlashcardReviewScope) => void
  onToggleCollapse: () => void
}) {
  const hasSelectedSources = selectedCount > 0
  const areToolsDisabled = !hasSelectedSources || !canStartGeneration
  const isFlashcardApp = mode === 'flashcards' && Boolean(flashcards)
  const isQuizApp = mode === 'quiz' && Boolean(quiz)
  const isStudyApp = isFlashcardApp || isQuizApp

  return (
    <section
      className={`interactive-panel studio-panel${isCollapsed ? ' is-collapsed' : ''}${
        isStudyApp ? ' is-app-mode' : ''
      }`}
      aria-label="扩展学习功能区"
    >
      <div className="interactive-panel-head">
        <h2>{isStudyApp ? 'Studio › 应用' : 'Studio'}</h2>
        <button
          className="icon-quiet-button panel-collapse-button"
          type="button"
          aria-label={isCollapsed ? '展开 Studio' : '折叠 Studio'}
          aria-expanded={!isCollapsed}
          onClick={onToggleCollapse}
        >
          <CollapsePanelIcon size={20} />
        </button>
      </div>

      <div className="panel-transition-body">
        <div
          className={`panel-view panel-expanded-view${isCollapsed ? ' is-hidden' : ''}`}
          aria-hidden={isCollapsed}
        >
          {isQuizApp && quiz ? (
          <QuizPracticeApp
            quiz={quiz}
            documents={documents}
            selectedAnswers={selectedAnswers}
            revealedQuestions={revealedQuestions}
            activeQuestionIndex={activeQuizQuestionIndex}
            studyQuestionIds={quizStudyQuestionIds}
            isSourceListOpen={isSourceListOpen}
            isRestartMenuOpen={isQuizRestartMenuOpen}
            onBack={onCloseStudioApp}
            onSelectAnswer={onSelectAnswer}
            onRevealQuestion={onRevealQuestion}
            onRecordQuizPractice={onRecordQuizPractice}
            onNextQuestion={onNextQuizQuestion}
            onExplainMistake={onExplainQuizMistake}
            onToggleSourceList={onToggleSourceList}
            onToggleRestartMenu={onToggleQuizRestartMenu}
            onRestartQuiz={onRestartQuiz}
          />
        ) : isFlashcardApp && flashcards ? (
          <FlashcardPracticeApp
            flashcards={flashcards}
            documents={documents}
            records={practiceRecords.filter(
              (record) => record.flashcard_set_id === flashcards.flashcard_set_id,
            )}
            activeCardIndex={activeCardIndex}
            isCardFlipped={isCardFlipped}
            studyCardIds={studyCardIds}
            cardFeedback={cardFeedback}
            isSourceListOpen={isSourceListOpen}
            isRestartMenuOpen={isRestartMenuOpen}
            onBack={onCloseStudioApp}
            onPreviousCard={onPreviousCard}
            onNextCard={onNextCard}
            onFlipCard={onFlipCard}
            onMarkFlashcard={onMarkFlashcard}
            onExplainFlashcard={onExplainFlashcard}
            onToggleSourceList={onToggleSourceList}
            onToggleRestartMenu={onToggleRestartMenu}
            onRestartFlashcards={onRestartFlashcards}
          />
        ) : (
          <>
            <div className="studio-tool-grid">
              <button
                type="button"
                className={`studio-tool-card quiz${areToolsDisabled ? ' is-unavailable' : ''}`}
                onClick={onGenerateQuiz}
                disabled={areToolsDisabled}
              >
                <span className="studio-tool-icon">
                  <QuizToolIcon size={24} />
                </span>
                <span>测验</span>
                <ChevronRight size={18} strokeWidth={2.2} />
              </button>
              <button
                type="button"
                className={`studio-tool-card flashcard${areToolsDisabled ? ' is-unavailable' : ''}`}
                onClick={onGenerateFlashcards}
                disabled={areToolsDisabled}
              >
                <span className="studio-tool-icon">
                  <FlashcardToolIcon size={24} />
                </span>
                <span>闪卡</span>
                <ChevronRight size={18} strokeWidth={2.2} />
              </button>
            </div>

            <div className="studio-output">
              {pendingGenerations.map((pendingGeneration) => (
                <StudioGeneratingItem
                  kind={pendingGeneration.kind}
                  selectedCount={pendingGeneration.selectedCount}
                  key={pendingGeneration.id}
                />
              ))}

              {!isGenerating && errorMessage.length > 0 ? <p className="interactive-error">{errorMessage}</p> : null}

              <StudioArtifactList
                quizzes={quizzes}
                flashcardSets={flashcardSets}
                onOpenQuiz={onOpenQuiz}
                onOpenFlashcards={onOpenFlashcards}
                onViewQuizSources={onViewQuizSources}
                onViewFlashcardSources={onViewFlashcardSources}
                onDeleteQuiz={onDeleteQuiz}
                onDeleteFlashcards={onDeleteFlashcards}
              />

              {!isGenerating && quizzes.length === 0 && flashcardSets.length === 0 && errorMessage.length === 0 ? (
                <div className="studio-empty-state">
                  <Sparkles size={26} strokeWidth={1.8} />
                  <strong>Studio 输出将保存在此处</strong>
                  <p>选择来源后，点击测验或闪卡生成学习材料</p>
                </div>
              ) : null}
            </div>
          </>
        )}
        </div>

        <div
          className={`panel-view panel-collapsed-view${isCollapsed ? '' : ' is-hidden'}`}
          aria-hidden={!isCollapsed}
        >
          <StudioCollapsedRail
          hasSelectedSources={hasSelectedSources}
          hasQuiz={quizzes.length > 0}
          hasFlashcards={flashcardSets.length > 0}
          canStartGeneration={canStartGeneration}
          onGenerateQuiz={onGenerateQuiz}
          onGenerateFlashcards={onGenerateFlashcards}
          onOpenQuiz={() => {
            const firstQuiz = quizzes[0]
            if (firstQuiz) {
              onOpenQuiz(firstQuiz)
            }
          }}
          onOpenFlashcards={() => {
            const firstFlashcardSet = flashcardSets[0]
            if (firstFlashcardSet) {
              onOpenFlashcards(firstFlashcardSet)
            }
          }}
          />
        </div>
      </div>
    </section>
  )
}

function StudioGeneratingItem({
  kind,
  selectedCount,
}: {
  kind: Exclude<StudioGenerationKind, null>
  selectedCount: number
}) {
  return (
    <div className={`studio-generating-item is-${kind}`} aria-live="polite">
      <span>
        <Loader2 size={21} strokeWidth={2} />
      </span>
      <div>
        <strong>{kind === 'quiz' ? '正在生成测验...' : '正在生成闪卡...'}</strong>
        <p>基于 {selectedCount} 个来源</p>
      </div>
    </div>
  )
}

function StudioArtifactList({
  quizzes,
  flashcardSets,
  onOpenQuiz,
  onOpenFlashcards,
  onViewQuizSources,
  onViewFlashcardSources,
  onDeleteQuiz,
  onDeleteFlashcards,
}: {
  quizzes: ClassroomQuizGenerateResult[]
  flashcardSets: ClassroomFlashcardsGenerateResult[]
  onOpenQuiz: (quiz: ClassroomQuizGenerateResult) => void
  onOpenFlashcards: (flashcardSet: ClassroomFlashcardsGenerateResult) => void
  onViewQuizSources: (quiz: ClassroomQuizGenerateResult) => void
  onViewFlashcardSources: (flashcardSet: ClassroomFlashcardsGenerateResult) => void
  onDeleteQuiz: (quizId: string) => void
  onDeleteFlashcards: (flashcardSetId: string) => void
}) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [menuAnchorElement, setMenuAnchorElement] = useState<HTMLButtonElement | null>(null)
  const activeFlashcardSet = openMenuId?.startsWith('flashcards-')
    ? flashcardSets.find((flashcardSet) => `flashcards-${flashcardSet.flashcard_set_id}` === openMenuId)
    : null
  const activeQuiz = openMenuId?.startsWith('quiz-')
    ? quizzes.find((quizItem) => `quiz-${quizItem.quiz_id}` === openMenuId)
    : null

  function closeMenu() {
    setOpenMenuId(null)
    setMenuAnchorElement(null)
  }

  if (quizzes.length === 0 && flashcardSets.length === 0) {
    return null
  }

  return (
    <div className="studio-artifact-list" aria-label="已生成的 Studio 内容">
      {flashcardSets.map((flashcardSet) => {
        const menuId = `flashcards-${flashcardSet.flashcard_set_id}`
        return (
          <article
            className="studio-artifact-row is-flashcards"
            key={flashcardSet.flashcard_set_id}
          >
            <button
              className="studio-artifact-open"
              type="button"
              onClick={() => {
                setOpenMenuId(null)
                onOpenFlashcards(flashcardSet)
              }}
            >
              <span className="studio-artifact-icon">
                <FlashcardToolIcon size={22} />
              </span>
              <span className="studio-artifact-main">
                <strong>{flashcardSet.title}</strong>
                <small>
                  {flashcardSet.cards.length} 张卡 · {formatArtifactTime(flashcardSet.created_at)}
                </small>
              </span>
            </button>
            <div className="studio-artifact-menu-anchor">
              <button
                className="studio-artifact-more-button"
                type="button"
                aria-label="更多闪卡操作"
                aria-haspopup="menu"
                aria-expanded={openMenuId === menuId}
                onClick={(event) => {
                  const isOpen = openMenuId === menuId
                  setOpenMenuId(isOpen ? null : menuId)
                  setMenuAnchorElement(isOpen ? null : event.currentTarget)
                }}
              >
                <MoreHorizontal size={18} strokeWidth={2} />
              </button>
            </div>
          </article>
        )
      })}

      {quizzes.map((quizItem) => {
        const menuId = `quiz-${quizItem.quiz_id}`
        return (
          <article className="studio-artifact-row is-quiz" key={quizItem.quiz_id}>
            <button
              className="studio-artifact-open"
              type="button"
              onClick={() => {
                setOpenMenuId(null)
                onOpenQuiz(quizItem)
              }}
            >
              <span className="studio-artifact-icon">
                <QuizToolIcon size={22} />
              </span>
              <span className="studio-artifact-main">
                <strong>{quizItem.title}</strong>
                <small>
                  {quizItem.questions.length} 题 · {formatArtifactTime(quizItem.created_at)}
                </small>
              </span>
            </button>
            <div className="studio-artifact-menu-anchor">
              <button
                className="studio-artifact-more-button"
                type="button"
                aria-label="更多测验操作"
                aria-haspopup="menu"
                aria-expanded={openMenuId === menuId}
                onClick={(event) => {
                  const isOpen = openMenuId === menuId
                  setOpenMenuId(isOpen ? null : menuId)
                  setMenuAnchorElement(isOpen ? null : event.currentTarget)
                }}
              >
                <MoreHorizontal size={18} strokeWidth={2} />
              </button>
            </div>
          </article>
        )
      })}
      {activeFlashcardSet ? (
        <StudioArtifactActionMenu
          anchorElement={menuAnchorElement}
          onClose={closeMenu}
          onViewSources={() => {
            closeMenu()
            onViewFlashcardSources(activeFlashcardSet)
          }}
          onDelete={() => {
            closeMenu()
            onDeleteFlashcards(activeFlashcardSet.flashcard_set_id)
          }}
        />
      ) : null}
      {activeQuiz ? (
        <StudioArtifactActionMenu
          anchorElement={menuAnchorElement}
          onClose={closeMenu}
          onViewSources={() => {
            closeMenu()
            onViewQuizSources(activeQuiz)
          }}
          onDelete={() => {
            closeMenu()
            onDeleteQuiz(activeQuiz.quiz_id)
          }}
        />
      ) : null}
    </div>
  )
}

function StudioArtifactActionMenu({
  anchorElement,
  onClose,
  onViewSources,
  onDelete,
}: {
  anchorElement: HTMLElement | null
  onClose: () => void
  onViewSources: () => void
  onDelete: () => void
}) {
  return (
    <FloatingActionMenu
      anchorElement={anchorElement}
      className="studio-artifact-action-menu"
      menuWidth={168}
      menuHeight={88}
      onClose={onClose}
    >
      <button type="button" role="menuitem" onClick={onViewSources}>
        <FileText size={17} strokeWidth={1.9} />
        查看来源
      </button>
      <button type="button" role="menuitem" onClick={onDelete}>
        <Trash2 size={17} strokeWidth={1.9} />
        删除
      </button>
    </FloatingActionMenu>
  )
}
function StudioCollapsedRail({
  hasSelectedSources,
  hasQuiz,
  hasFlashcards,
  canStartGeneration,
  onGenerateQuiz,
  onGenerateFlashcards,
  onOpenQuiz,
  onOpenFlashcards,
}: {
  hasSelectedSources: boolean
  hasQuiz: boolean
  hasFlashcards: boolean
  canStartGeneration: boolean
  onGenerateQuiz: () => void
  onGenerateFlashcards: () => void
  onOpenQuiz: () => void
  onOpenFlashcards: () => void
}) {
  const areToolsDisabled = !hasSelectedSources || !canStartGeneration

  return (
    <div className="studio-collapsed-rail" aria-label="折叠后的 Studio">
      <div className="studio-rail-tool-list">
        <button
          className={`studio-rail-tool is-quiz${!hasSelectedSources ? ' is-unavailable' : ''}`}
          type="button"
          aria-label="生成测验"
          onClick={onGenerateQuiz}
          disabled={areToolsDisabled}
      >
        <QuizToolIcon size={22} />
        <span className="studio-rail-tool-add" aria-hidden="true">+</span>
      </button>
        <button
          className={`studio-rail-tool is-flashcard${!hasSelectedSources ? ' is-unavailable' : ''}`}
          type="button"
          aria-label="生成闪卡"
          onClick={onGenerateFlashcards}
          disabled={areToolsDisabled}
      >
        <FlashcardToolIcon size={22} />
        <span className="studio-rail-tool-add" aria-hidden="true">+</span>
      </button>
      </div>

      {hasQuiz || hasFlashcards ? (
        <div className="studio-rail-artifact-list">
          {hasQuiz ? (
            <button className="studio-rail-artifact is-quiz" type="button" aria-label="查看测验" onClick={onOpenQuiz}>
              <QuizToolIcon size={23} />
            </button>
          ) : null}
          {hasFlashcards ? (
            <button
              className="studio-rail-artifact is-flashcard"
              type="button"
              aria-label="查看闪卡"
              onClick={onOpenFlashcards}
            >
              <FlashcardToolIcon size={23} />
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function QuizPracticeApp({
  quiz,
  documents,
  selectedAnswers,
  revealedQuestions,
  activeQuestionIndex,
  studyQuestionIds,
  isSourceListOpen,
  isRestartMenuOpen,
  onBack,
  onSelectAnswer,
  onRevealQuestion,
  onRecordQuizPractice,
  onNextQuestion,
  onExplainMistake,
  onToggleSourceList,
  onToggleRestartMenu,
  onRestartQuiz,
}: {
  quiz: ClassroomQuizGenerateResult
  documents: RAGDocumentSummary[]
  selectedAnswers: Record<string, string>
  revealedQuestions: Set<string>
  activeQuestionIndex: number
  studyQuestionIds: string[]
  isSourceListOpen: boolean
  isRestartMenuOpen: boolean
  onBack: () => void
  onSelectAnswer: (questionId: string, answer: string) => void
  onRevealQuestion: (questionId: string) => void
  onRecordQuizPractice: (question: QuizQuestion, selectedAnswer: string) => void
  onNextQuestion: () => void
  onExplainMistake: (question: QuizQuestion) => void
  onToggleSourceList: () => void
  onToggleRestartMenu: () => void
  onRestartQuiz: (scope: QuizReviewScope) => void
}) {
  const studyQuestions = quiz.questions.filter((question) =>
    studyQuestionIds.includes(question.question_id),
  )
  const activeQuestion = studyQuestions[activeQuestionIndex] ?? studyQuestions[0]
  const stats = quizStats(studyQuestions, selectedAnswers, revealedQuestions)
  const sourceDocuments = quiz.source_document_ids.map((documentId) => {
    const document = documents.find((item) => item.document_id === documentId)
    return {
      id: documentId,
      filename: document?.filename ?? documentId,
      title: document ? sourceDisplayName(document) : documentId,
    }
  })

  return (
    <div className="quiz-app">
      <div className="flashcard-app-toolbar">
        <span />
        <button className="icon-quiet-button app-minimize-button" type="button" aria-label="返回 Studio 列表" onClick={onBack}>
          <Minimize2 size={17} strokeWidth={2} />
        </button>
      </div>

      <div className="flashcard-app-title">
        <h3>{quiz.title}</h3>
        <button type="button" onClick={onToggleSourceList}>
          查看 {sourceDocuments.length} 个来源
        </button>
        {isSourceListOpen ? <FlashcardSourcesPopover sources={sourceDocuments} /> : null}
      </div>

      {stats.isComplete ? (
        <FlashcardCompletionSummary
          stats={stats}
          labels={{
            completeTitle: stats.incorrect > 0 ? '再接再厉' : '全部答对',
            correct: '答对',
            incorrect: '答错',
            skipped: '未答',
            restartAll: '全部题目',
            restartIncorrect: '仅答错的题目',
          }}
          isRestartMenuOpen={isRestartMenuOpen}
          onToggleRestartMenu={onToggleRestartMenu}
          onRestartFlashcards={onRestartQuiz}
        />
      ) : activeQuestion ? (
        <QuizQuestionStage
          question={activeQuestion}
          index={activeQuestionIndex}
          total={studyQuestions.length}
          selectedAnswer={selectedAnswers[activeQuestion.question_id] ?? ''}
          isRevealed={revealedQuestions.has(activeQuestion.question_id)}
          onSelectAnswer={onSelectAnswer}
          onRevealQuestion={onRevealQuestion}
          onRecordPractice={onRecordQuizPractice}
          onNextQuestion={onNextQuestion}
          onExplainMistake={onExplainMistake}
        />
      ) : (
        <div className="studio-empty-state">
          <Sparkles size={26} strokeWidth={1.8} />
          <strong>没有可练习的题目</strong>
        </div>
      )}
    </div>
  )
}

function QuizQuestionStage({
  question,
  index,
  total,
  selectedAnswer,
  isRevealed,
  onSelectAnswer,
  onRevealQuestion,
  onRecordPractice,
  onNextQuestion,
  onExplainMistake,
}: {
  question: QuizQuestion
  index: number
  total: number
  selectedAnswer: string
  isRevealed: boolean
  onSelectAnswer: (questionId: string, answer: string) => void
  onRevealQuestion: (questionId: string) => void
  onRecordPractice: (question: QuizQuestion, selectedAnswer: string) => void
  onNextQuestion: () => void
  onExplainMistake: (question: QuizQuestion) => void
}) {
  const answeredWrong = isRevealed && selectedAnswer !== question.answer

  function handleSelect(option: string) {
    if (isRevealed) {
      return
    }
    onSelectAnswer(question.question_id, option)
    onRevealQuestion(question.question_id)
    onRecordPractice(question, option)
  }

  return (
    <div className="quiz-stage">
      <article className={`quiz-question-card${isRevealed ? ' is-revealed' : ''}`}>
        <span>{index + 1}/{total}</span>
        <strong>{question.stem}</strong>
        <div className="quiz-app-options">
          {question.options.map((option, optionIndex) => {
            const isSelected = selectedAnswer === option
            const isCorrect = question.answer === option
            return (
              <button
                className={`quiz-app-option${isSelected ? ' is-selected' : ''}${
                  isRevealed && isCorrect ? ' is-correct' : ''
                }${isRevealed && isSelected && !isCorrect ? ' is-wrong' : ''}`}
                type="button"
                onClick={() => handleSelect(option)}
                disabled={isRevealed}
                key={option}
              >
                <span className="quiz-option-letter">{optionLetter(optionIndex)}.</span>
                <span className="quiz-option-copy">
                  <strong>{displayQuizOption(option)}</strong>
                  {isRevealed ? (
                    <>
                      {isSelected && isCorrect ? (
                        <small className="is-correct">
                          <Check size={14} strokeWidth={2.3} />
                          正确
                        </small>
                      ) : null}
                      {isSelected && !isCorrect ? (
                        <small className="is-wrong">
                          <X size={14} strokeWidth={2.3} />
                          不太对
                        </small>
                      ) : null}
                      {!isSelected && isCorrect ? (
                        <small className="is-correct">
                          <Check size={14} strokeWidth={2.3} />
                          正确答案
                        </small>
                      ) : null}
                      <p>{optionExplanation(question, option)}</p>
                    </>
                  ) : null}
                </span>
              </button>
            )
          })}
        </div>
      </article>

      <div className="quiz-action-row">
        {answeredWrong ? (
          <button className="secondary-compact-button" type="button" onClick={() => onExplainMistake(question)}>
            <Clipboard size={16} strokeWidth={2} />
            解释
          </button>
        ) : (
          <span aria-hidden="true" />
        )}
        <button
          className="quiz-next-button"
          type="button"
          onClick={onNextQuestion}
          disabled={!isRevealed}
        >
          下一个
        </button>
      </div>
    </div>
  )
}

function FlashcardPracticeApp({
  flashcards,
  documents,
  records,
  activeCardIndex,
  isCardFlipped,
  studyCardIds,
  cardFeedback,
  isSourceListOpen,
  isRestartMenuOpen,
  onBack,
  onPreviousCard,
  onNextCard,
  onFlipCard,
  onMarkFlashcard,
  onExplainFlashcard,
  onToggleSourceList,
  onToggleRestartMenu,
  onRestartFlashcards,
}: {
  flashcards: ClassroomFlashcardsGenerateResult
  documents: RAGDocumentSummary[]
  records: FlashcardPracticeRecord[]
  activeCardIndex: number
  isCardFlipped: boolean
  studyCardIds: string[]
  cardFeedback: FlashcardPracticeResult | null
  isSourceListOpen: boolean
  isRestartMenuOpen: boolean
  onBack: () => void
  onPreviousCard: () => void
  onNextCard: () => void
  onFlipCard: () => void
  onMarkFlashcard: (result: FlashcardPracticeResult) => void
  onExplainFlashcard: (card: FlashcardItem) => void
  onToggleSourceList: () => void
  onToggleRestartMenu: () => void
  onRestartFlashcards: (scope: FlashcardReviewScope) => void
}) {
  const studyCards = flashcards.cards.filter((card) => studyCardIds.includes(card.card_id))
  const activeCard = studyCards[activeCardIndex]
  const stats = flashcardStats(studyCards, records)
  const recordByCard = practiceRecordMap(records)
  const activeRecord = activeCard ? recordByCard.get(activeCard.card_id) : undefined
  const visibleFeedback = cardFeedback ?? activeRecord?.result ?? null
  const sourceDocuments = flashcards.source_document_ids.map((documentId) => {
    const document = documents.find((item) => item.document_id === documentId)
    return {
      id: documentId,
      filename: document?.filename ?? documentId,
      title: document ? sourceDisplayName(document) : documentId,
    }
  })

  return (
    <div className="flashcard-app">
      <div className="flashcard-app-header">
        <div className="flashcard-app-title">
          <h3>{flashcards.title}</h3>
          <button type="button" onClick={onToggleSourceList}>
            查看 {sourceDocuments.length} 个来源
          </button>
          {isSourceListOpen ? <FlashcardSourcesPopover sources={sourceDocuments} /> : null}
        </div>
        <button className="icon-quiet-button app-minimize-button" type="button" aria-label="返回 Studio 列表" onClick={onBack}>
          <Minimize2 size={17} strokeWidth={2} />
        </button>
      </div>

      {stats.isComplete && !activeCard ? (
        <FlashcardCompletionSummary
          stats={stats}
          isRestartMenuOpen={isRestartMenuOpen}
          onToggleRestartMenu={onToggleRestartMenu}
          onRestartFlashcards={onRestartFlashcards}
        />
      ) : activeCard ? (
        <>
          <div className="flashcard-stage">
            <article
              className={`flashcard-study-card${isCardFlipped ? ' is-answer' : ''}${
                recordByCard.has(activeCard.card_id) ? ' is-recorded' : ''
              }`}
              role="button"
              tabIndex={0}
              aria-label={isCardFlipped ? '显示闪卡题目' : '显示闪卡答案'}
              onClick={onFlipCard}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onFlipCard()
                }
              }}
            >
              <span>{activeCardIndex + 1}/{studyCards.length}</span>
              <strong>{isCardFlipped ? activeCard.back : activeCard.front}</strong>
              {isCardFlipped ? (
                <button
                  className="flashcard-explain-button"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    onExplainFlashcard(activeCard)
                  }}
                >
                  解释
                </button>
              ) : (
                <span className="flashcard-answer-label">查看答案</span>
              )}
              {visibleFeedback ? (
                <div className={`flashcard-feedback is-${visibleFeedback}`}>
                  {visibleFeedback === 'correct' ? '明白了' : '没明白'}
                </div>
              ) : null}
            </article>
          </div>

          <div className="flashcard-practice-controls">
            <button type="button" onClick={onPreviousCard} disabled={activeCardIndex === 0} aria-label="上一张卡片">
              <ChevronLeft size={22} strokeWidth={2} />
            </button>
            <button
              className="is-wrong"
              type="button"
              onClick={() => onMarkFlashcard('incorrect')}
              disabled={Boolean(cardFeedback)}
            >
              <X size={19} strokeWidth={2.2} />
              {stats.incorrect}
            </button>
            <button
              className="is-right"
              type="button"
              onClick={() => onMarkFlashcard('correct')}
              disabled={Boolean(cardFeedback)}
            >
              {stats.correct}
              <Check size={19} strokeWidth={2.2} />
            </button>
            <button
              type="button"
              onClick={onNextCard}
              disabled={activeCardIndex >= studyCards.length - 1}
              aria-label="下一张卡片"
            >
              <ChevronRight size={22} strokeWidth={2} />
            </button>
          </div>
        </>
      ) : (
        <div className="studio-empty-state">
          <Sparkles size={26} strokeWidth={1.8} />
          <strong>没有可练习的卡片</strong>
        </div>
      )}
    </div>
  )
}

function FlashcardSourcesPopover({
  sources,
}: {
  sources: Array<{ id: string; filename: string; title: string }>
}) {
  return (
    <div className="flashcard-source-popover" role="dialog" aria-label="闪卡来源">
      <strong>来源</strong>
      <div>
        {sources.map((source) => (
          <span className="flashcard-source-item" key={source.id}>
            <FileTypeIcon filename={source.filename} />
            {source.title}
          </span>
        ))}
      </div>
    </div>
  )
}

function FlashcardCompletionSummary({
  stats,
  labels = {
    completeTitle: stats.incorrect > 0 ? '再接再厉' : '全部完成',
    correct: '明白了',
    incorrect: '没明白',
    skipped: '未作答',
    restartAll: '所有卡片',
    restartIncorrect: '仅没明白的卡片',
  },
  isRestartMenuOpen,
  onToggleRestartMenu,
  onRestartFlashcards,
}: {
  stats: PracticeStats
  labels?: {
    completeTitle: string
    correct: string
    incorrect: string
    skipped: string
    restartAll: string
    restartIncorrect: string
  }
  isRestartMenuOpen: boolean
  onToggleRestartMenu: () => void
  onRestartFlashcards: (scope: FlashcardReviewScope) => void
}) {
  const percent = stats.total > 0 ? Math.round((stats.correct / stats.total) * 100) : 0
  const circumference = 2 * Math.PI * 44
  const offset = circumference - (circumference * percent) / 100

  return (
    <div className="flashcard-completion">
      <div className="flashcard-completion-card">
        <h3>{labels.completeTitle}</h3>
        <div className="flashcard-score-box">
          <div className="flashcard-score-visual">
            <svg viewBox="0 0 112 112" aria-hidden="true">
              <circle cx="56" cy="56" r="44" />
              <circle cx="56" cy="56" r="44" style={{ strokeDasharray: circumference, strokeDashoffset: offset }} />
            </svg>
            <div className="flashcard-score-copy">
              <strong>{stats.correct}/{stats.total}</strong>
              <span>{percent}%</span>
            </div>
          </div>
          <dl>
            <div>
              <dt>{labels.correct}</dt>
              <dd>{stats.correct}</dd>
            </div>
            <div>
              <dt>{labels.incorrect}</dt>
              <dd>{stats.incorrect}</dd>
            </div>
            <div>
              <dt>{labels.skipped}</dt>
              <dd>{stats.skipped}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="flashcard-restart">
        {isRestartMenuOpen ? (
          <div className="flashcard-restart-menu">
            <button type="button" onClick={() => onRestartFlashcards('all')}>{labels.restartAll}</button>
            <button type="button" onClick={() => onRestartFlashcards('incorrect')}>{labels.restartIncorrect}</button>
          </div>
        ) : null}
        <button className="flashcard-restart-button" type="button" onClick={onToggleRestartMenu}>
          <RotateCcw size={16} strokeWidth={2} />
          再练习一次
          <ChevronRight size={15} strokeWidth={2} />
        </button>
      </div>
    </div>
  )
}

function Classroom() {
  const notebook = useOutletContext<NotebookSummary>()
  const courseId = notebook.course_id
  const notebookId = notebook.notebook_id
  const knowledgePointId = notebook.knowledge_point_id
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const userId = getActiveUserId()
  const visitId = useNotebookVisitId()
  const [documents, setDocuments] = useNotebookSessionState<RAGDocumentSummary[]>(
    'sources:documents',
    [],
  )
  const [selectedIds, setSelectedIds] = useNotebookSessionState<Set<string>>(
    'classroom:selectedSourceIds',
    () => new Set(),
  )
  const [chatError, setChatError] = useState('')
  const [studioError, setStudioError] = useState('')
  const [isLoadingSources, setIsLoadingSources] = useState(documents.length === 0)
  const [isUploading, setIsUploading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useNotebookSessionState<ChatMessage[]>(
    'classroom:messages',
    [],
  )
  const [studioMode, setStudioMode] = useState<StudioMode>('empty')
  const [quiz, setQuiz] = useState<ClassroomQuizGenerateResult | null>(null)
  const [flashcards, setFlashcards] = useState<ClassroomFlashcardsGenerateResult | null>(null)
  const [quizzes, setQuizzes] = useState<ClassroomQuizGenerateResult[]>([])
  const [flashcardSets, setFlashcardSets] = useState<ClassroomFlashcardsGenerateResult[]>([])
  const [flashcardRecords, setFlashcardRecords] = useState<FlashcardPracticeRecord[]>([])
  const [pendingStudioGenerations, setPendingStudioGenerations] = useState<PendingStudioGeneration[]>([])
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({})
  const [revealedQuestions, setRevealedQuestions] = useState<Set<string>>(new Set())
  const [activeQuizQuestionIndex, setActiveQuizQuestionIndex] = useState(0)
  const [quizStudyQuestionIds, setQuizStudyQuestionIds] = useState<string[]>([])
  const [activeCardIndex, setActiveCardIndex] = useState(0)
  const [isCardFlipped, setIsCardFlipped] = useState(false)
  const [studyCardIds, setStudyCardIds] = useState<string[]>([])
  const [flashcardAttemptId, setFlashcardAttemptId] = useState('')
  const [cardFeedback, setCardFeedback] = useState<FlashcardPracticeResult | null>(null)
  const [isFlashcardSourceListOpen, setIsFlashcardSourceListOpen] = useState(false)
  const [isQuizRestartMenuOpen, setIsQuizRestartMenuOpen] = useState(false)
  const [isRestartMenuOpen, setIsRestartMenuOpen] = useState(false)
  const [isSourcePanelCollapsed, setIsSourcePanelCollapsed] = useState(false)
  const [isStudioPanelCollapsed, setIsStudioPanelCollapsed] = useState(false)
  const [isSourceDialogOpen, setIsSourceDialogOpen] = useState(false)
  const [sourceDialogMode, setSourceDialogMode] = useState<SourceDialogMode>('files')
  const [pastedSourceText, setPastedSourceText] = useState('')
  const hasInitializedSourcesRef = useRef(documents.length > 0)
  const activeFlashcardAttemptIdRef = useRef<string | null>(null)
  const flashcardCompletionTimerRef = useRef<number | null>(null)
  const isRecordingFlashcardRef = useRef(false)
  const chatRequestIdRef = useRef(0)
  const pendingStudioGenerationCountRef = useRef(0)

  useEffect(
    () => () => {
      if (flashcardCompletionTimerRef.current !== null) {
        window.clearTimeout(flashcardCompletionTimerRef.current)
      }
    },
    [],
  )

  function cancelFlashcardCompletionTransition() {
    if (flashcardCompletionTimerRef.current !== null) {
      window.clearTimeout(flashcardCompletionTimerRef.current)
      flashcardCompletionTimerRef.current = null
    }
  }

  function beginFlashcardAttempt(cardIds: string[]) {
    cancelFlashcardCompletionTransition()
    const attemptId = createFlashcardAttemptId()
    activeFlashcardAttemptIdRef.current = attemptId
    setFlashcardAttemptId(attemptId)
    setStudyCardIds(cardIds)
    setActiveCardIndex(0)
    setIsCardFlipped(false)
    setCardFeedback(null)
    setIsRestartMenuOpen(false)
  }

  const applySourceDocuments = useCallback((items: RAGDocumentSummary[]) => {
    const serverIds = new Set(items.map((item) => item.document_id))
    setDocuments((current) => {
      const localItems = current.filter(
        (item) => item.metadata.local === 'true' && !serverIds.has(item.document_id),
      )
      return [...localItems, ...items]
    })
    setSelectedIds((current) => {
      const readyItems = items.filter(isSourceReady)
      const next = new Set(
        [...current].filter((id) => serverIds.has(id) || id.startsWith('pending-')),
      )
      if (!hasInitializedSourcesRef.current && next.size === 0) {
        readyItems.forEach((item) => next.add(item.document_id))
      }
      return next
    })
    hasInitializedSourcesRef.current = true
  }, [])

  const refreshSourceDocuments = useCallback(async () => {
    const result = await ragApi.documents({
      user_id: userId,
      course_id: courseId,
      notebook_id: notebookId,
    })
    applySourceDocuments(result.items)
    return result.items
  }, [applySourceDocuments, courseId, notebookId, userId])

  useEffect(() => {
    let isCurrent = true

    async function loadDocuments() {
      setIsLoadingSources(true)
      try {
        const result = await ragApi.documents({
          user_id: userId,
          course_id: courseId,
          notebook_id: notebookId,
        })
        if (!isCurrent) {
          return
        }

        applySourceDocuments(result.items)
      } catch {
        return
      } finally {
        if (isCurrent) {
          setIsLoadingSources(false)
        }
      }
    }

    void loadDocuments()

    return () => {
      isCurrent = false
    }
  }, [applySourceDocuments, courseId, notebookId, userId])

  useEffect(() => {
    const hasRemoteProcessingSource = documents.some(
      (document) => isSourceProcessing(document) && document.metadata.local !== 'true',
    )
    if (!hasRemoteProcessingSource) {
      return
    }

    const timer = window.setInterval(() => {
      void refreshSourceDocuments().catch(() => undefined)
    }, 1400)

    return () => window.clearInterval(timer)
  }, [documents, refreshSourceDocuments])

  useEffect(() => {
    let isCurrent = true

    async function loadStudioArtifacts() {
      try {
        const result = await classroomApi.studio({
          user_id: userId,
          course_id: courseId,
          notebook_id: notebookId,
        })
        if (!isCurrent) {
          return
        }
        setQuizzes(result.quizzes)
        setFlashcardSets(result.flashcard_sets)
        setFlashcardRecords([])
      } catch {
        if (isCurrent) {
          setStudioError('')
        }
      }
    }

    void loadStudioArtifacts()

    return () => {
      isCurrent = false
    }
  }, [courseId, notebookId, userId])

  const readyDocuments = useMemo(
    () => documents.filter(isSourceReady),
    [documents],
  )
  const selectedDocuments = useMemo(
    () => readyDocuments.filter((document) => selectedIds.has(document.document_id)),
    [readyDocuments, selectedIds],
  )
  const selectedDocumentIds = useMemo(
    () => selectedDocuments.map((document) => document.document_id),
    [selectedDocuments],
  )
  const chatScopeSourceCount = selectedDocumentIds.length
  const documentsById = useMemo(
    () => new Map(documents.map((document) => [document.document_id, document])),
    [documents],
  )
  const isGeneratingStudio = pendingStudioGenerations.length > 0
  const canStartStudioGeneration =
    pendingStudioGenerations.length < MAX_PENDING_STUDIO_GENERATIONS

  function reserveStudioGeneration(
    kind: Exclude<StudioGenerationKind, null>,
  ): PendingStudioGeneration | null {
    if (pendingStudioGenerationCountRef.current >= MAX_PENDING_STUDIO_GENERATIONS) {
      return null
    }
    const pendingGeneration = {
      id: createStudioGenerationId(),
      kind,
      selectedCount: selectedDocumentIds.length,
    }
    pendingStudioGenerationCountRef.current += 1
    setPendingStudioGenerations((current) => [...current, pendingGeneration])
    return pendingGeneration
  }

  function releaseStudioGeneration(generationId: string) {
    pendingStudioGenerationCountRef.current = Math.max(
      0,
      pendingStudioGenerationCountRef.current - 1,
    )
    setPendingStudioGenerations((current) =>
      current.filter((generation) => generation.id !== generationId),
    )
  }

  function handleAddSource() {
    setSourceDialogMode('files')
    setIsSourceDialogOpen(true)
  }

  function handleOpenFilePicker() {
    fileInputRef.current?.click()
  }

  function handleCloseSourceDialog() {
    if (isUploading) {
      return
    }
    setIsSourceDialogOpen(false)
    setSourceDialogMode('files')
    setPastedSourceText('')
  }

  async function uploadSourceFiles(files: File[]) {
    if (files.length === 0) {
      return
    }

    const pendingDocuments = files.map((file) =>
      createPendingSource(file, userId, courseId, notebookId),
    )
    setDocuments((current) => [...pendingDocuments, ...current])
    setSelectedIds((current) => new Set([...current, ...pendingDocuments.map((item) => item.document_id)]))
    setIsSourceDialogOpen(false)
    setSourceDialogMode('files')
    setPastedSourceText('')
    setIsUploading(true)
    try {
      for (const [index, file] of files.entries()) {
        const pendingDocument = pendingDocuments[index]
        const uploadResult = await ragApi.uploadFile({
          user_id: userId,
          course_id: courseId,
          notebook_id: notebookId,
          file,
        })
        const uploadedDocument = uploadResult.document ?? {
          ...pendingDocument,
          document_id: uploadResult.document_id,
          source_id: uploadResult.source_id,
          upload_status: uploadResult.upload_status,
          chunk_count: uploadResult.chunk_count,
          metadata: { ...pendingDocument.metadata, local: 'false' },
        }
        setDocuments((current) =>
          current.map((document) =>
            document.document_id === pendingDocument.document_id ? uploadedDocument : document,
          ),
        )
        setSelectedIds((current) => {
          const next = new Set(current)
          if (next.delete(pendingDocument.document_id)) {
            next.add(uploadResult.document_id)
          }
          return next
        })
      }
      void refreshSourceDocuments().catch(() => undefined)
    } catch {
      const pendingIds = new Set(pendingDocuments.map((document) => document.document_id))
      setDocuments((current) =>
        current.filter((document) => !pendingIds.has(document.document_id)),
      )
      setSelectedIds((current) => {
        const next = new Set(current)
        pendingIds.forEach((documentId) => next.delete(documentId))
        return next
      })
      void refreshSourceDocuments().catch(() => undefined)
    } finally {
      setIsUploading(false)
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    await uploadSourceFiles(files)
    event.target.value = ''
  }

  async function handleSubmitPastedSource() {
    const content = pastedSourceText.trim()
    if (!content) {
      return
    }
    const file = new globalThis.File([content], PASTED_TEXT_UPLOAD_FILENAME, {
      type: 'text/plain;charset=utf-8',
    })
    await uploadSourceFiles([file])
  }

  function handleToggleSource(documentId: string) {
    const document = documentsById.get(documentId)
    if (!document || !isSourceReady(document)) {
      return
    }
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(documentId)) {
        next.delete(documentId)
      } else {
        next.add(documentId)
      }
      return next
    })
  }

  function handleToggleAllSources() {
    setSelectedIds((current) => {
      if (
        readyDocuments.length > 0 &&
        readyDocuments.every((document) => current.has(document.document_id))
      ) {
        return new Set()
      }
      return new Set(readyDocuments.map((document) => document.document_id))
    })
  }

  async function handleDeleteSource(documentId: string) {
    try {
      await ragApi.deleteDocument(documentId)
      setDocuments((current) =>
        current.filter((document) => document.document_id !== documentId),
      )
      setSelectedIds((current) => {
        const next = new Set(current)
        next.delete(documentId)
        return next
      })
    } catch {
      return
    }
  }

  async function askQuestion(
    question: string,
    sourceDocumentIds: string[] = selectedDocumentIds,
  ) {
    if (!question) {
      setChatError('请先输入问题。')
      return
    }
    if (readyDocuments.length === 0) {
      setChatError('请先上传来源，并等待处理完成后再提问。')
      return
    }
    if (sourceDocumentIds.length === 0) {
      setChatError('请至少选择一个来源后再提问。')
      return
    }
    const usesSelectedSubset =
      sourceDocumentIds.length > 0 && sourceDocumentIds.length < readyDocuments.length
    const requestSourceDocumentIds = usesSelectedSubset ? sourceDocumentIds : []

    const requestId = chatRequestIdRef.current + 1
    chatRequestIdRef.current = requestId
    const assistantMessageId = `${Date.now()}-assistant`
    const userMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: question,
    }
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
    }
    setMessages((current) => [...current, userMessage, assistantMessage])
    setDraft('')
    setChatError('')
    setIsAsking(true)

    let streamedAnswer = ''

    try {
      const answer = await classroomApi.askStream(
        {
          user_id: userId,
          course_id: courseId,
          notebook_id: notebookId,
          visit_id: visitId,
          knowledge_point_id: knowledgePointId,
          question,
          source_document_ids: requestSourceDocumentIds,
        },
        (delta) => {
          if (chatRequestIdRef.current !== requestId) {
            return
          }
          streamedAnswer += delta
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId ? { ...message, content: streamedAnswer } : message,
            ),
          )
        },
      )
      if (chatRequestIdRef.current !== requestId) {
        return
      }
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content: answer.answer || streamedAnswer,
                guidanceSteps: answer.guidance_steps,
              }
            : message,
        ),
      )
    } catch (error) {
      if (chatRequestIdRef.current !== requestId) {
        return
      }
      setMessages((current) =>
        current.filter(
          (message) =>
            message.id !== assistantMessageId || message.content.trim().length > 0,
        ),
      )
      setChatError(`问答失败：${toErrorMessage(error)}`)
    } finally {
      if (chatRequestIdRef.current === requestId) {
        setIsAsking(false)
      }
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await askQuestion(draft.trim())
  }

  async function handleGenerateQuiz() {
    if (readyDocuments.length === 0) {
      setStudioError('')
      return
    }
    if (selectedDocumentIds.length === 0) {
      setStudioError('')
      return
    }
    const pendingGeneration = reserveStudioGeneration('quiz')
    if (!pendingGeneration) {
      return
    }

    setStudioMode('empty')
    setStudioError('')
    setSelectedAnswers({})
    setRevealedQuestions(new Set())
    setActiveQuizQuestionIndex(0)
    setQuizStudyQuestionIds([])
    setIsQuizRestartMenuOpen(false)
    try {
      const result = await retryStudioGeneration(() =>
        classroomApi.generateQuiz({
          user_id: userId,
          course_id: courseId,
          notebook_id: notebookId,
          knowledge_point_id: knowledgePointId,
          source_document_ids: selectedDocumentIds,
        }),
      )
      setQuiz(result)
      setQuizStudyQuestionIds(result.questions.map((question) => question.question_id))
      setQuizzes((current) => [
        result,
        ...current.filter((item) => item.quiz_id !== result.quiz_id),
      ])
    } catch {
      return
    } finally {
      releaseStudioGeneration(pendingGeneration.id)
    }
  }

  async function handleGenerateFlashcards() {
    if (readyDocuments.length === 0) {
      setStudioError('')
      return
    }
    if (selectedDocumentIds.length === 0) {
      setStudioError('')
      return
    }
    const pendingGeneration = reserveStudioGeneration('flashcards')
    if (!pendingGeneration) {
      return
    }

    setStudioMode('empty')
    setStudioError('')
    setActiveCardIndex(0)
    setIsCardFlipped(false)
    try {
      const result = await retryStudioGeneration(() =>
        classroomApi.generateFlashcards({
          user_id: userId,
          course_id: courseId,
          notebook_id: notebookId,
          knowledge_point_id: knowledgePointId,
          source_document_ids: selectedDocumentIds,
        }),
      )
      setFlashcards(result)
      setFlashcardSets((current) => [
        result,
        ...current.filter((item) => item.flashcard_set_id !== result.flashcard_set_id),
      ])
    } catch {
      return
    } finally {
      releaseStudioGeneration(pendingGeneration.id)
    }
  }

  function handleOpenQuiz(quizItem: ClassroomQuizGenerateResult) {
    setQuiz(quizItem)
    setStudioMode('quiz')
    setSelectedAnswers({})
    setRevealedQuestions(new Set())
    setQuizStudyQuestionIds(quizItem.questions.map((question) => question.question_id))
    setActiveQuizQuestionIndex(0)
    setIsFlashcardSourceListOpen(false)
    setIsQuizRestartMenuOpen(false)
    setIsStudioPanelCollapsed(false)
  }

  function handleOpenFlashcards(flashcardSet: ClassroomFlashcardsGenerateResult) {
    setFlashcards(flashcardSet)
    setStudioMode('flashcards')
    beginFlashcardAttempt(flashcardSet.cards.map((card) => card.card_id))
    setIsFlashcardSourceListOpen(false)
    setIsStudioPanelCollapsed(false)
  }

  async function handleDeleteChatHistory() {
    chatRequestIdRef.current += 1
    try {
      await classroomApi.deleteHistory({
        user_id: userId,
        visit_id: visitId,
      })
      setMessages([])
      setChatError('')
    } catch (error) {
      setChatError(`删除对话记录失败：${toErrorMessage(error)}`)
    }
  }

  function handleViewQuizSources(quizItem: ClassroomQuizGenerateResult) {
    handleOpenQuiz(quizItem)
    setIsFlashcardSourceListOpen(true)
  }

  function handleViewFlashcardSources(flashcardSet: ClassroomFlashcardsGenerateResult) {
    handleOpenFlashcards(flashcardSet)
    setIsFlashcardSourceListOpen(true)
  }

  async function handleDeleteQuiz(quizId: string) {
    try {
      await classroomApi.deleteQuiz({
        quiz_id: quizId,
        user_id: userId,
      })
      setQuizzes((current) => current.filter((item) => item.quiz_id !== quizId))
      if (quiz?.quiz_id === quizId) {
        setQuiz(null)
        setSelectedAnswers({})
        setRevealedQuestions(new Set())
        setQuizStudyQuestionIds([])
        setActiveQuizQuestionIndex(0)
        handleCloseStudioApp()
      }
      setStudioError('')
    } catch {
      setStudioError('')
    }
  }

  async function handleDeleteFlashcards(flashcardSetId: string) {
    try {
      await classroomApi.deleteFlashcards({
        flashcard_set_id: flashcardSetId,
        user_id: userId,
      })
      setFlashcardSets((current) =>
        current.filter((item) => item.flashcard_set_id !== flashcardSetId),
      )
      setFlashcardRecords((current) =>
        current.filter((record) => record.flashcard_set_id !== flashcardSetId),
      )
      if (flashcards?.flashcard_set_id === flashcardSetId) {
        cancelFlashcardCompletionTransition()
        activeFlashcardAttemptIdRef.current = null
        setFlashcards(null)
        setFlashcardAttemptId('')
        setStudyCardIds([])
        setActiveCardIndex(0)
        setIsCardFlipped(false)
        setCardFeedback(null)
        handleCloseStudioApp()
      }
      setStudioError('')
    } catch {
      setStudioError('')
    }
  }

  function handleCloseStudioApp() {
    cancelFlashcardCompletionTransition()
    activeFlashcardAttemptIdRef.current = null
    setFlashcardAttemptId('')
    setStudioMode('empty')
    setIsCardFlipped(false)
    setCardFeedback(null)
    setIsFlashcardSourceListOpen(false)
    setIsQuizRestartMenuOpen(false)
    setIsRestartMenuOpen(false)
  }

  function handleNextQuizQuestion() {
    setActiveQuizQuestionIndex((current) =>
      Math.min(Math.max(0, quizStudyQuestionIds.length - 1), current + 1),
    )
  }

  function handleExplainQuizMistake(question: QuizQuestion) {
    if (!quiz) {
      return
    }
    const selectedAnswer = selectedAnswers[question.question_id]
    if (!selectedAnswer || selectedAnswer === question.answer) {
      return
    }
    void askQuestion(
      buildQuizMistakePrompt(question, selectedAnswer),
      quiz.source_document_ids,
    )
  }

  function handleRestartQuiz(scope: QuizReviewScope) {
    if (!quiz) {
      return
    }
    const incorrectIds = quiz.questions
      .filter(
        (question) =>
          revealedQuestions.has(question.question_id) &&
          selectedAnswers[question.question_id] !== question.answer,
      )
      .map((question) => question.question_id)
    const nextStudyIds =
      scope === 'incorrect' && incorrectIds.length > 0
        ? incorrectIds
        : quiz.questions.map((question) => question.question_id)

    setSelectedAnswers({})
    setRevealedQuestions(new Set())
    setQuizStudyQuestionIds(nextStudyIds)
    setActiveQuizQuestionIndex(0)
    setIsQuizRestartMenuOpen(false)
  }

  async function handleRecordQuizPractice(
    question: QuizQuestion,
    selectedAnswer: string,
  ) {
    if (!quiz) {
      return
    }
    try {
      await classroomApi.recordQuizPractice({
        user_id: userId,
        course_id: courseId,
        quiz_id: quiz.quiz_id,
        question_id: question.question_id,
        selected_answer: selectedAnswer,
      })
    } catch {
      setStudioError('')
    }
  }

  async function handleMarkFlashcard(result: FlashcardPracticeResult) {
    const attemptId = activeFlashcardAttemptIdRef.current
    if (!flashcards || !attemptId || cardFeedback || isRecordingFlashcardRef.current) {
      return
    }

    const studyCards = flashcards.cards.filter((card) => studyCardIds.includes(card.card_id))
    const activeCard = studyCards[activeCardIndex]
    if (!activeCard) {
      return
    }

    isRecordingFlashcardRef.current = true
    try {
      const record = await classroomApi.recordFlashcardPractice({
        user_id: userId,
        course_id: courseId,
        flashcard_set_id: flashcards.flashcard_set_id,
        attempt_id: attemptId,
        study_card_ids: studyCardIds,
        card_id: activeCard.card_id,
        result,
      })
      if (activeFlashcardAttemptIdRef.current !== attemptId) {
        return
      }
      setFlashcardRecords((current) => [
        ...current.filter(
          (item) =>
            !(
              item.flashcard_set_id === record.flashcard_set_id &&
              item.attempt_id === record.attempt_id &&
              item.card_id === record.card_id
            ),
        ),
        record,
      ])
      setCardFeedback(result)
      if (record.attempt_completed) {
        cancelFlashcardCompletionTransition()
        flashcardCompletionTimerRef.current = window.setTimeout(() => {
          if (activeFlashcardAttemptIdRef.current === attemptId) {
            setCardFeedback(null)
            setIsCardFlipped(false)
            setActiveCardIndex(studyCards.length)
          }
          flashcardCompletionTimerRef.current = null
        }, 620)
      }
    } catch {
      setStudioError('')
    } finally {
      isRecordingFlashcardRef.current = false
    }
  }

  function handleExplainFlashcard(card: FlashcardItem) {
    if (!flashcards) {
      return
    }
    void askQuestion(
      buildFlashcardExplainPrompt(card),
      flashcards.source_document_ids,
    )
  }

  function handleRestartFlashcards(scope: FlashcardReviewScope) {
    const completedAttemptId = activeFlashcardAttemptIdRef.current
    if (!flashcards || !completedAttemptId) {
      return
    }

    const currentRecords = flashcardRecords.filter(
      (record) =>
        record.flashcard_set_id === flashcards.flashcard_set_id &&
        record.attempt_id === completedAttemptId,
    )
    const incorrectIds = currentRecords
      .filter((record) => record.result === 'incorrect')
      .map((record) => record.card_id)
    const nextStudyIds =
      scope === 'incorrect' && incorrectIds.length > 0
        ? incorrectIds
        : flashcards.cards.map((card) => card.card_id)

    beginFlashcardAttempt(nextStudyIds)
  }

  return (
    <div
      className={`interactive-classroom${isSourcePanelCollapsed ? ' is-source-collapsed' : ''}${
        isStudioPanelCollapsed ? ' is-studio-collapsed' : ''
      }${
        ((studioMode === 'flashcards' && flashcards) || (studioMode === 'quiz' && quiz)) &&
        !isStudioPanelCollapsed
          ? ' is-studio-expanded'
          : ''
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={SOURCE_FILE_ACCEPT}
        onChange={handleUpload}
        multiple
        hidden
      />
      <SourceDialog
        isOpen={isSourceDialogOpen}
        mode={sourceDialogMode}
        isUploading={isUploading}
        pastedText={pastedSourceText}
        onClose={handleCloseSourceDialog}
        onModeChange={setSourceDialogMode}
        onPastedTextChange={setPastedSourceText}
        onUploadClick={handleOpenFilePicker}
        onFilesDrop={(files) => {
          void uploadSourceFiles(files)
        }}
        onSubmitText={() => {
          void handleSubmitPastedSource()
        }}
      />
      <SourcePanel
        documents={documents}
        selectedIds={selectedIds}
        isLoading={isLoadingSources}
        isUploading={isUploading}
        isCollapsed={isSourcePanelCollapsed}
        onAddSource={handleAddSource}
        onToggle={handleToggleSource}
        onToggleAll={handleToggleAllSources}
        onDeleteSource={(documentId) => {
          void handleDeleteSource(documentId)
        }}
        onToggleCollapse={() => setIsSourcePanelCollapsed((current) => !current)}
      />
      <ChatPanel
        messages={messages}
        draft={draft}
        selectedCount={chatScopeSourceCount}
        sourceCount={readyDocuments.length}
        notebookTitle={notebook.title}
        isAsking={isAsking}
        errorMessage={chatError}
        onDraftChange={setDraft}
        onSubmit={handleAsk}
        onDeleteMessages={() => {
          void handleDeleteChatHistory()
        }}
      />
      <StudioPanel
        mode={studioMode}
        selectedCount={selectedDocumentIds.length}
        quiz={quiz}
        flashcards={flashcards}
        quizzes={quizzes}
        flashcardSets={flashcardSets}
        documents={documents}
        practiceRecords={flashcardRecords.filter(
          (record) => record.attempt_id === flashcardAttemptId,
        )}
        pendingGenerations={pendingStudioGenerations}
        isGenerating={isGeneratingStudio}
        canStartGeneration={canStartStudioGeneration}
        isCollapsed={isStudioPanelCollapsed}
        errorMessage={studioError}
        revealedQuestions={revealedQuestions}
        selectedAnswers={selectedAnswers}
        activeQuizQuestionIndex={activeQuizQuestionIndex}
        quizStudyQuestionIds={quizStudyQuestionIds}
        activeCardIndex={activeCardIndex}
        isCardFlipped={isCardFlipped}
        studyCardIds={studyCardIds}
        cardFeedback={cardFeedback}
        isSourceListOpen={isFlashcardSourceListOpen}
        isQuizRestartMenuOpen={isQuizRestartMenuOpen}
        isRestartMenuOpen={isRestartMenuOpen}
        onGenerateQuiz={handleGenerateQuiz}
        onGenerateFlashcards={handleGenerateFlashcards}
        onOpenQuiz={handleOpenQuiz}
        onOpenFlashcards={handleOpenFlashcards}
        onViewQuizSources={handleViewQuizSources}
        onViewFlashcardSources={handleViewFlashcardSources}
        onDeleteQuiz={(quizId) => {
          void handleDeleteQuiz(quizId)
        }}
        onDeleteFlashcards={(flashcardSetId) => {
          void handleDeleteFlashcards(flashcardSetId)
        }}
        onCloseStudioApp={handleCloseStudioApp}
        onSelectAnswer={(questionId, answer) =>
          setSelectedAnswers((current) => ({ ...current, [questionId]: answer }))
        }
        onRevealQuestion={(questionId) =>
          setRevealedQuestions((current) => new Set([...current, questionId]))
        }
        onRecordQuizPractice={(question, selectedAnswer) => {
          void handleRecordQuizPractice(question, selectedAnswer)
        }}
        onNextQuizQuestion={handleNextQuizQuestion}
        onExplainQuizMistake={handleExplainQuizMistake}
        onToggleQuizRestartMenu={() => setIsQuizRestartMenuOpen((current) => !current)}
        onRestartQuiz={handleRestartQuiz}
        onPreviousCard={() => {
          setActiveCardIndex((current) => Math.max(0, current - 1))
          setIsCardFlipped(false)
          setCardFeedback(null)
        }}
        onNextCard={() => {
          setActiveCardIndex((current) => Math.min(studyCardIds.length - 1, current + 1))
          setIsCardFlipped(false)
          setCardFeedback(null)
        }}
        onFlipCard={() => setIsCardFlipped((current) => !current)}
        onMarkFlashcard={(result) => {
          void handleMarkFlashcard(result)
        }}
        onExplainFlashcard={handleExplainFlashcard}
        onToggleSourceList={() => setIsFlashcardSourceListOpen((current) => !current)}
        onToggleRestartMenu={() => setIsRestartMenuOpen((current) => !current)}
        onRestartFlashcards={(scope) => {
          void handleRestartFlashcards(scope)
        }}
        onToggleCollapse={() => setIsStudioPanelCollapsed((current) => !current)}
      />
    </div>
  )
}

export default Classroom
