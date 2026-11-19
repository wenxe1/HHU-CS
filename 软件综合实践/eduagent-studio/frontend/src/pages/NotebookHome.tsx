import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import {
  ChevronDown,
  MoreVertical,
  Pencil,
  Pin,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import AccountMenu from '../components/AccountMenu'
import { getActiveUserId } from '../lib/auth'
import { notebookApi, type NotebookSummary } from '../lib/api'

type NotebookSort = 'recent' | 'title'

function formatNotebookDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '刚刚'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
}

function pinnedStorageKey(userId: string) {
  return `eduagent:notebook:pinned:${userId}`
}

function readPinnedNotebookIds(userId: string) {
  try {
    const value = window.localStorage.getItem(pinnedStorageKey(userId))
    const parsed = value ? JSON.parse(value) : []
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === 'string')
      : []
  } catch {
    return []
  }
}

function writePinnedNotebookIds(userId: string, notebookIds: string[]) {
  try {
    window.localStorage.setItem(pinnedStorageKey(userId), JSON.stringify(notebookIds))
  } catch {
    return
  }
}

function NotebookHome() {
  const navigate = useNavigate()
  const userId = getActiveUserId()
  const nameInputRef = useRef<HTMLInputElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([])
  const [sortMode, setSortMode] = useState<NotebookSort>('recent')
  const [isSortOpen, setIsSortOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [notebookName, setNotebookName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [openNotebookMenuId, setOpenNotebookMenuId] = useState<string | null>(null)
  const [pinnedNotebookIds, setPinnedNotebookIds] = useState<string[]>(() =>
    readPinnedNotebookIds(userId),
  )

  useEffect(() => {
    let isCurrent = true

    async function loadNotebooks() {
      setIsLoading(true)
      try {
        const result = await notebookApi.list(userId)
        if (isCurrent) {
          setNotebooks(result)
        }
      } catch {
        if (isCurrent) {
          setNotebooks([])
        }
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    void loadNotebooks()
    return () => {
      isCurrent = false
    }
  }, [userId])

  useEffect(() => {
    writePinnedNotebookIds(userId, pinnedNotebookIds)
  }, [pinnedNotebookIds, userId])

  useEffect(() => {
    if (!isCreateOpen) {
      return
    }

    nameInputRef.current?.focus()
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isCreating) {
        setIsCreateOpen(false)
      }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [isCreateOpen, isCreating])

  useEffect(() => {
    if (!isSearchOpen) {
      return
    }

    searchInputRef.current?.focus()
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsSearchOpen(false)
        setSearchTerm('')
      }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [isSearchOpen])

  useEffect(() => {
    if (!openNotebookMenuId) {
      return
    }

    function closeOnOutsidePointer(event: PointerEvent) {
      const target = event.target as Element | null
      if (
        target?.closest('.notebook-card-menu') ||
        target?.closest('.notebook-card-action-menu')
      ) {
        return
      }
      setOpenNotebookMenuId(null)
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpenNotebookMenuId(null)
      }
    }

    document.addEventListener('pointerdown', closeOnOutsidePointer)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [openNotebookMenuId])

  const sortedNotebooks = useMemo(() => {
    const pinnedRank = new Map(
      pinnedNotebookIds.map((notebookId, index) => [notebookId, index]),
    )
    const items = [...notebooks]
    if (sortMode === 'title') {
      items.sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'))
    } else {
      items.sort(
        (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
      )
    }
    return items.sort((a, b) => {
      const aPinned = pinnedRank.has(a.notebook_id)
      const bPinned = pinnedRank.has(b.notebook_id)
      if (aPinned && bPinned) {
        return pinnedRank.get(a.notebook_id)! - pinnedRank.get(b.notebook_id)!
      }
      if (aPinned) {
        return -1
      }
      if (bPinned) {
        return 1
      }
      return 0
    })
  }, [notebooks, pinnedNotebookIds, sortMode])

  const searchQuery = searchTerm.trim()
  const visibleNotebooks = useMemo(() => {
    if (!searchQuery) {
      return sortedNotebooks
    }
    const normalizedQuery = searchQuery.toLocaleLowerCase('zh-CN')
    return sortedNotebooks.filter((notebook) =>
      notebook.title.toLocaleLowerCase('zh-CN').includes(normalizedQuery),
    )
  }, [searchQuery, sortedNotebooks])

  const isFiltering = isSearchOpen && searchQuery.length > 0
  const hasSearchResults = visibleNotebooks.length > 0

  function selectSortMode(nextMode: NotebookSort) {
    setSortMode(nextMode)
    setIsSortOpen(false)
  }

  function openSearch() {
    setIsSortOpen(false)
    setIsSearchOpen(true)
  }

  function closeSearch() {
    setIsSearchOpen(false)
    setSearchTerm('')
  }

  function clearSearch() {
    setSearchTerm('')
    searchInputRef.current?.focus()
  }

  function openCreateDialog() {
    setNotebookName('')
    setIsCreateOpen(true)
  }

  function closeCreateDialog() {
    if (!isCreating) {
      setIsCreateOpen(false)
    }
  }

  async function createNotebook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const title = notebookName.trim()
    if (!title || isCreating) {
      return
    }

    setIsCreating(true)
    try {
      const notebook = await notebookApi.create({ user_id: userId, title })
      setNotebooks((current) => [notebook, ...current])
      setIsCreateOpen(false)
      navigate(`/notebooks/${encodeURIComponent(notebook.notebook_id)}`)
    } catch {
      return
    } finally {
      setIsCreating(false)
    }
  }

  function togglePinnedNotebook(notebookId: string) {
    setPinnedNotebookIds((current) =>
      current.includes(notebookId)
        ? current.filter((currentId) => currentId !== notebookId)
        : [notebookId, ...current],
    )
    setOpenNotebookMenuId(null)
  }

  async function renameNotebook(notebook: NotebookSummary) {
    const nextTitle = window.prompt('修改标题', notebook.title)?.trim()
    setOpenNotebookMenuId(null)
    if (!nextTitle || nextTitle === notebook.title) {
      return
    }

    try {
      const updated = await notebookApi.rename(notebook.notebook_id, {
        user_id: userId,
        title: nextTitle,
      })
      setNotebooks((current) =>
        current.map((item) =>
          item.notebook_id === updated.notebook_id ? updated : item,
        ),
      )
    } catch {
      return
    }
  }

  async function deleteNotebook(notebookId: string) {
    setOpenNotebookMenuId(null)

    try {
      await notebookApi.delete(notebookId, userId)
      setNotebooks((current) =>
        current.filter((notebook) => notebook.notebook_id !== notebookId),
      )
      setPinnedNotebookIds((current) =>
        current.filter((currentId) => currentId !== notebookId),
      )
    } catch {
      return
    }
  }

  return (
    <div className="notebook-home">
      <header className={`notebook-home-header${isSearchOpen ? ' is-searching' : ''}`}>
        <Link className="notebook-home-brand" to="/" aria-label="EduAgent Studio">
          <img src="/favicon.svg" alt="" />
          <span>EduAgent Studio</span>
        </Link>

        {isSearchOpen ? (
          <AccountMenu compact />
        ) : (
          <div className="notebook-home-actions">
            <button
              className="notebook-icon-button"
              type="button"
              aria-label="搜索笔记本"
              onClick={openSearch}
            >
              <Search size={24} strokeWidth={1.75} />
            </button>

            <div className="notebook-sort">
              <button
                className="notebook-sort-button"
                type="button"
                aria-haspopup="menu"
                aria-expanded={isSortOpen}
                onClick={() => setIsSortOpen((current) => !current)}
              >
                {sortMode === 'recent' ? '最近' : '标题'}
                <ChevronDown size={16} strokeWidth={2.2} />
              </button>

              {isSortOpen ? (
                <div className="notebook-sort-menu" role="menu">
                  <button type="button" role="menuitem" onClick={() => selectSortMode('recent')}>
                    最近
                  </button>
                  <button type="button" role="menuitem" onClick={() => selectSortMode('title')}>
                    标题
                  </button>
                </div>
              ) : null}
            </div>

            <button className="notebook-new-button" type="button" onClick={openCreateDialog}>
              <Plus size={22} strokeWidth={2.4} />
              新建
            </button>

            <AccountMenu compact />
          </div>
        )}
      </header>

      <main className={`notebook-home-main${isSearchOpen ? ' is-searching' : ''}`}>
        {isSearchOpen ? (
          <div className="notebook-home-search-row">
            <label className="notebook-search-field">
              <Search size={22} strokeWidth={1.9} />
              <input
                ref={searchInputRef}
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="按笔记本标题搜索"
              />
              {searchTerm ? (
                <button type="button" aria-label="清除搜索内容" onClick={clearSearch}>
                  <X size={22} strokeWidth={2.1} />
                </button>
              ) : null}
            </label>
            <button className="notebook-search-cancel" type="button" onClick={closeSearch}>
              取消
            </button>
          </div>
        ) : null}

        {isFiltering && !hasSearchResults ? (
          <section className="notebook-search-empty" aria-live="polite">
            <Search size={48} strokeWidth={1.75} />
            <strong>未找到任何笔记本</strong>
            <p>请尝试搜索其他笔记本标题</p>
            <button type="button" onClick={clearSearch}>
              清除搜索内容
            </button>
          </section>
        ) : (
          <>
            {isFiltering ? (
              <p className="notebook-search-result-count">
                搜索结果（{visibleNotebooks.length}条）
              </p>
            ) : null}
            <h1>我的笔记本</h1>

            {isLoading ? <p className="notebook-home-status">正在加载笔记本...</p> : null}

            <section className="notebook-grid" aria-label="我的笔记本">
              {!isFiltering ? (
                <button
                  className="notebook-card notebook-create-card"
                  type="button"
                  onClick={openCreateDialog}
                >
                  <span className="notebook-create-icon">
                    <Plus size={26} strokeWidth={1.9} />
                  </span>
                  <strong>新建笔记本</strong>
                </button>
              ) : null}

              {visibleNotebooks.map((notebook) => {
                const isPinned = pinnedNotebookIds.includes(notebook.notebook_id)
                const isMenuOpen = openNotebookMenuId === notebook.notebook_id
                return (
                  <article
                    className="notebook-card notebook-course-card tone-sage"
                    key={notebook.notebook_id}
                  >
                    <Link
                      className="notebook-card-link"
                      to={`/notebooks/${encodeURIComponent(notebook.notebook_id)}`}
                    >
                      <span className="notebook-card-icon" aria-hidden="true">📖</span>
                      <span className="notebook-card-spacer" />
                      <strong>{notebook.title}</strong>
                      <small>
                        {formatNotebookDate(notebook.created_at)} · {notebook.source_count} 个来源
                      </small>
                    </Link>
                    {isPinned ? (
                      <span className="notebook-card-pin" aria-label="已置顶">
                        <Pin size={19} strokeWidth={2.1} />
                      </span>
                    ) : null}
                    <button
                      className="notebook-card-menu"
                      type="button"
                      aria-label={`${notebook.title} 更多操作`}
                      aria-haspopup="menu"
                      aria-expanded={isMenuOpen}
                      onClick={() =>
                        setOpenNotebookMenuId((current) =>
                          current === notebook.notebook_id ? null : notebook.notebook_id,
                        )
                      }
                    >
                      <MoreVertical size={22} strokeWidth={2.1} />
                    </button>
                    {isMenuOpen ? (
                      <div className="notebook-card-action-menu" role="menu">
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            void deleteNotebook(notebook.notebook_id)
                          }}
                        >
                          <Trash2 size={21} strokeWidth={2} />
                          删除
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            void renameNotebook(notebook)
                          }}
                        >
                          <Pencil size={21} strokeWidth={2} />
                          修改标题
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => togglePinnedNotebook(notebook.notebook_id)}
                        >
                          <Pin size={21} strokeWidth={2} />
                          {isPinned ? '取消置顶' : '置顶'}
                        </button>
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </section>
          </>
        )}
      </main>

      {isCreateOpen ? (
        <div
          className="notebook-dialog-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeCreateDialog()
            }
          }}
        >
          <section
            className="notebook-create-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="notebook-create-title"
          >
            <button
              className="notebook-dialog-close"
              type="button"
              aria-label="关闭"
              onClick={closeCreateDialog}
              disabled={isCreating}
            >
              <X size={21} strokeWidth={2} />
            </button>
            <form onSubmit={createNotebook}>
              <h2 id="notebook-create-title">新建笔记本</h2>
              <label htmlFor="notebook-name">笔记本名称</label>
              <input
                ref={nameInputRef}
                id="notebook-name"
                value={notebookName}
                onChange={(event) => setNotebookName(event.target.value)}
                placeholder="输入笔记本名称"
                maxLength={100}
                disabled={isCreating}
              />
              <div className="notebook-dialog-actions">
                <button type="button" onClick={closeCreateDialog} disabled={isCreating}>
                  取消
                </button>
                <button type="submit" disabled={isCreating || !notebookName.trim()}>
                  {isCreating ? '正在创建...' : '创建'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  )
}

export default NotebookHome
