import {
  BotMessageSquare,
  Check,
  ChevronDown,
  FileText,
  Loader2,
  MessageSquareText,
  Send,
  Trash2,
  X,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import ReactMarkdown from 'react-markdown'
import { useOutletContext } from 'react-router'
import remarkGfm from 'remark-gfm'
import {
  ragApi,
  resolveApiUrl,
  tutorApi,
  type NotebookSummary,
  type RAGDocumentSummary,
  type TutorAskResult,
} from '../lib/api'
import { getActiveUserId } from '../lib/auth'
import {
  useNotebookSessionState,
  useNotebookVisitId,
} from '../layouts/NotebookSessionContext'

type TutorMessageRole = 'user' | 'assistant'

interface TutorChatMessage {
  id: string
  role: TutorMessageRole
  content: string
}

function toErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '请求失败'
}

function sourceDisplayName(document: RAGDocumentSummary) {
  return (document.source_title || document.filename || '未命名来源').trim()
}

function isReadyPdfSource(document: RAGDocumentSummary) {
  const filename = document.filename.toLowerCase()
  return (
    document.upload_status === 'success' &&
    (filename.endsWith('.pdf') ||
      document.content_type === 'application/pdf' ||
      document.source_type === 'pdf' ||
      document.metadata.file_kind === 'pdf')
  )
}

function sourcePreviewUrl(document: RAGDocumentSummary) {
  const previewUrl = document.metadata.original_file_url || document.metadata.preview_url
  return previewUrl ? resolveApiUrl(previewUrl) : ''
}

function summarizeTutorResult(result: TutorAskResult) {
  const sections = [result.answer.trim()]
  if (result.guidance_steps.length > 0) {
    sections.push(`学习提示\n${result.guidance_steps.map((step, index) => `${index + 1}. ${step}`).join('\n')}`)
  }
  if (result.follow_up_questions.length > 0) {
    sections.push(`可以继续追问\n${result.follow_up_questions.map((item) => `- ${item}`).join('\n')}`)
  }
  return sections.filter(Boolean).join('\n\n')
}

function makeMessageId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function Tutor() {
  const activeUserId = getActiveUserId()
  const notebook = useOutletContext<NotebookSummary | null>()
  const visitId = useNotebookVisitId()
  const chatThreadRef = useRef<HTMLDivElement | null>(null)
  const typingTimerRef = useRef<number | null>(null)
  const pendingTypingRef = useRef<{ messageId: string; content: string } | null>(null)
  const requestIdRef = useRef(0)

  const [sources, setSources] = useNotebookSessionState<RAGDocumentSummary[]>(
    'sources:documents',
    [],
  )
  const [selectedSourceId, setSelectedSourceId] = useNotebookSessionState(
    'tutor:selectedSourceId',
    '',
  )
  const [isLoadingSources, setIsLoadingSources] = useState(sources.length === 0)
  const [isSourceMenuOpen, setIsSourceMenuOpen] = useState(false)
  const [sourceError, setSourceError] = useState('')
  const [chatDraft, setChatDraft] = useState('')
  const [chatMessages, setChatMessages] = useNotebookSessionState<TutorChatMessage[]>(
    'tutor:messages',
    [],
  )
  const [feedback, setFeedback] = useState('')
  const [isChatting, setIsChatting] = useState(false)
  const [isTyping, setIsTyping] = useState(false)

  const pdfSources = useMemo(
    () => sources.filter(isReadyPdfSource),
    [sources],
  )
  const selectedSource = useMemo(
    () => pdfSources.find((source) => source.document_id === selectedSourceId) ?? null,
    [pdfSources, selectedSourceId],
  )
  const selectedPreviewUrl = selectedSource ? sourcePreviewUrl(selectedSource) : ''

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

  function showAssistantMessage(content: string) {
    stopTyping()
    const assistantId = makeMessageId('assistant')
    let cursor = 0
    pendingTypingRef.current = { messageId: assistantId, content }
    setChatMessages((current) => [...current, { id: assistantId, role: 'assistant', content: '' }])
    setIsTyping(true)

    typingTimerRef.current = window.setInterval(() => {
      cursor += Math.max(1, Math.ceil(content.length / 80))
      setChatMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, content: content.slice(0, cursor) } : message,
        ),
      )
      if (cursor >= content.length) {
        stopTyping()
      }
    }, 18)
  }

  async function sendTutorMessage(rawQuestion: string) {
    const question = rawQuestion.trim()

    if (!question) {
      setFeedback('请先输入问题。')
      return
    }
    if (!selectedSource) {
      setFeedback('请先选择一个互动课堂中的 PDF 来源。')
      return
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    stopTyping()
    setFeedback('')
    setIsChatting(true)

    setChatMessages((current) => [...current, { id: makeMessageId('user'), role: 'user', content: question }])
    setChatDraft('')

    try {
      const result = await tutorApi.ask({
        user_id: activeUserId,
        question,
        notebook_id: notebook?.notebook_id || null,
        visit_id: visitId,
        course_id: notebook?.course_id || null,
        course_name: null,
        knowledge_point_id: notebook?.knowledge_point_id || null,
        knowledge_point_name: null,
        source_document_ids: [selectedSource.document_id],
        student_profile: {},
      })
      if (requestIdRef.current === requestId) {
        showAssistantMessage(summarizeTutorResult(result))
      }
    } catch (error) {
      if (requestIdRef.current === requestId) {
        setFeedback(`请求失败：${toErrorMessage(error)}`)
        showAssistantMessage('暂时无法连接辅导服务。你可以稍后重试，或换一个来源后继续提问。')
      }
    } finally {
      if (requestIdRef.current === requestId) {
        setIsChatting(false)
      }
    }
  }

  function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void sendTutorMessage(chatDraft)
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void sendTutorMessage(chatDraft)
    }
  }

  function clearChat() {
    requestIdRef.current += 1
    stopTyping(false)
    setChatMessages([])
    setChatDraft('')
    setFeedback('')
    setIsChatting(false)
  }

  useEffect(() => {
    let isCurrent = true

    async function loadSources() {
      if (!notebook) {
        setSources([])
        setSelectedSourceId('')
        return
      }

      setIsLoadingSources(true)
      setSourceError('')
      try {
        const result = await ragApi.documents({
          user_id: activeUserId,
          course_id: notebook.course_id,
          notebook_id: notebook.notebook_id,
        })
        if (!isCurrent) {
          return
        }
        setSources(result.items)
        setSelectedSourceId((current) =>
          current && result.items.some((item) => item.document_id === current && isReadyPdfSource(item))
            ? current
            : '',
        )
      } catch (error) {
        if (isCurrent) {
          setSourceError(`无法读取互动课堂来源：${toErrorMessage(error)}`)
        }
      } finally {
        if (isCurrent) {
          setIsLoadingSources(false)
        }
      }
    }

    void loadSources()

    return () => {
      isCurrent = false
    }
  }, [activeUserId, notebook])

  useEffect(
    () => () => {
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
    const thread = chatThreadRef.current
    if (!thread) {
      return
    }
    if (chatMessages.length === 0) {
      thread.scrollTo({ top: 0 })
      return
    }
    window.requestAnimationFrame(() => {
      thread.scrollTop = thread.scrollHeight
    })
  }, [chatMessages, isChatting, isTyping])

  return (
    <div className="tutor-v1-page">
      <section className="tutor-v1-grid">
        <section className="panel tutor-material-panel">
          <div className="tutor-panel-heading">
            <div className="tutor-heading-title">
              <FileText size={21} strokeWidth={1.9} />
              <h2>资料预览</h2>
            </div>

            <div className="tutor-upload-row">
              <div className="tutor-source-picker">
                <button
                  className="primary-action tutor-source-select-button"
                  type="button"
                  onClick={() => setIsSourceMenuOpen((current) => !current)}
                  disabled={pdfSources.length === 0}
                  aria-haspopup="menu"
                  aria-expanded={isSourceMenuOpen}
                >
                  {isLoadingSources && pdfSources.length === 0 ? (
                    <>
                      <Loader2 className="source-status-spin" size={16} strokeWidth={2} />
                      读取中
                    </>
                  ) : selectedSource ? (
                    '选择资料'
                  ) : (
                    '选择资料'
                  )}
                  {!(isLoadingSources && pdfSources.length === 0) ? (
                    <ChevronDown size={16} strokeWidth={2} />
                  ) : null}
                </button>

                {isSourceMenuOpen ? (
                  <div className="tutor-source-menu" role="menu">
                    {pdfSources.map((source) => {
                      const isSelected = selectedSourceId === source.document_id
                      return (
                        <button
                          type="button"
                          role="menuitem"
                          className={isSelected ? 'is-selected' : ''}
                          onClick={() => {
                            setSelectedSourceId(source.document_id)
                            setIsSourceMenuOpen(false)
                            setFeedback('')
                            setSourceError('')
                          }}
                          key={source.document_id}
                        >
                          <FileText size={16} strokeWidth={1.9} />
                          <span>{sourceDisplayName(source)}</span>
                          {isSelected ? <Check size={16} strokeWidth={2.2} /> : null}
                        </button>
                      )
                    })}
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          {selectedSource ? (
            <div className="tutor-file-card">
              <div>
                <strong>{sourceDisplayName(selectedSource)}</strong>
                <span>来自互动课堂来源</span>
              </div>
              <button type="button" aria-label="移除当前来源" onClick={() => setSelectedSourceId('')}>
                <X size={17} strokeWidth={2} />
              </button>
            </div>
          ) : null}

          <div className="tutor-file-preview">
            {isLoadingSources && !selectedSource ? (
              <div className="tutor-presentation-placeholder">
                <Loader2 className="source-status-spin" size={38} strokeWidth={1.8} />
                <strong>正在读取来源</strong>
                <span>正在从互动课堂同步可用的 PDF 来源。</span>
              </div>
            ) : !selectedSource ? (
              <div className="tutor-presentation-placeholder">
                <FileText size={42} strokeWidth={1.7} />
                <strong>{sourceError ? '来源读取失败' : pdfSources.length > 0 ? '选择一个 PDF 来源' : '暂无可选择的 PDF 来源'}</strong>
                <span>
                  {sourceError
                    ? sourceError
                    : pdfSources.length > 0
                    ? '从右上角选择互动课堂来源后，将在这里显示 PDF 预览。'
                    : '请先在互动课堂来源栏添加并处理完成 PDF 文件。'}
                </span>
              </div>
            ) : selectedPreviewUrl ? (
              <object className="tutor-file-object" data={selectedPreviewUrl} type="application/pdf">
                <iframe src={selectedPreviewUrl} title={sourceDisplayName(selectedSource)} />
              </object>
            ) : (
              <div className="tutor-presentation-placeholder">
                <FileText size={42} strokeWidth={1.7} />
                <strong>{sourceDisplayName(selectedSource)}</strong>
                <span>该来源上传时未保存原始 PDF，请在互动课堂重新添加一次该 PDF 后预览；仍可基于已解析内容提问。</span>
              </div>
            )}
          </div>
        </section>

        <section className="panel tutor-chat-panel-v1">
          <div className="tutor-panel-heading">
            <div className="tutor-heading-title">
              <BotMessageSquare size={22} strokeWidth={1.9} />
              <h2>AI 学习助手</h2>
            </div>
          </div>

          <div
            className={`tutor-chat-thread-v1 ${
              chatMessages.length === 0 && !isChatting ? 'is-empty' : ''
            }`}
            ref={chatThreadRef}
            aria-live="polite"
          >
            {chatMessages.length === 0 ? (
              <div className="tutor-chat-empty">
                <MessageSquareText size={32} strokeWidth={1.8} />
                <strong>选择资料后开始提问</strong>
                <span>你可以基于左侧正在查看的 PDF，询问概念、例题或章节内容。</span>
              </div>
            ) : (
              chatMessages.map((message, index) => (
                <article
                  className={`tutor-chat-message-v1 ${message.role} ${
                    isTyping && message.role === 'assistant' && index === chatMessages.length - 1 ? 'is-typing' : ''
                  }`}
                  key={message.id}
                >
                  <span>{message.role === 'user' ? '你' : 'AI 助手'}</span>
                  {message.role === 'assistant' && message.content ? (
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{message.content || '正在组织回答...'}</p>
                  )}
                </article>
              ))
            )}
            {isChatting ? (
              <article className="tutor-chat-message-v1 assistant is-loading">
                <span>AI 助手</span>
                <p>正在思考...</p>
              </article>
            ) : null}
          </div>

          {feedback ? <p className="tutor-v1-feedback">{feedback}</p> : null}

          <form className="tutor-chat-composer-v1" onSubmit={handleChatSubmit}>
            <textarea
              value={chatDraft}
              onChange={(event) => setChatDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              rows={4}
              placeholder="输入关于当前资料的问题"
            />
            <div>
              <button type="button" aria-label="清空对话" onClick={clearChat}>
                <Trash2 size={17} strokeWidth={2} />
              </button>
              <button type="submit" aria-label="发送问题" disabled={isChatting || !chatDraft.trim()}>
                <Send size={17} strokeWidth={2} />
              </button>
            </div>
          </form>
        </section>
      </section>
    </div>
  )
}

export default Tutor
