import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation, useParams } from 'react-router'
import AccountMenu from '../components/AccountMenu'
import Sidebar from '../components/Sidebar'
import { navigationItems } from '../data/navigation'
import { getActiveUserId } from '../lib/auth'
import { classroomApi, notebookApi, type NotebookSummary } from '../lib/api'
import { NotebookSessionProvider } from './NotebookSessionProvider'

function createNotebookVisitId() {
  return globalThis.crypto?.randomUUID?.() ?? `visit-${Date.now()}-${Math.random()}`
}

function NotebookVisit({
  notebook,
}: {
  notebook: NotebookSummary
}) {
  const [visitId] = useState(createNotebookVisitId)

  return (
    <NotebookSessionProvider visitId={visitId}>
      <Outlet context={notebook} />
    </NotebookSessionProvider>
  )
}

function AppLayout() {
  const location = useLocation()
  const { notebookId = '' } = useParams()
  const userId = getActiveUserId()
  const currentSection = location.pathname.split('/').filter(Boolean).at(-1) ?? 'classroom'
  const activeItem =
    navigationItems.find((item) => item.path === currentSection) ?? navigationItems[0]
  const isClassroom = activeItem.path === 'classroom'
  const isTopbarHidden = ['classroom', 'resources', 'tutor', 'profile'].includes(activeItem.path)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [notebook, setNotebook] = useState<NotebookSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    if (!notebookId) {
      return
    }

    let isCurrent = true

    async function loadNotebook() {
      setIsLoading(true)
      setLoadError('')
      setNotebook(null)
      try {
        const result = await notebookApi.detail(notebookId, userId)
        if (isCurrent) {
          setNotebook(result)
          void classroomApi
            .generateProfile({
              user_id: userId,
              course_id: result.course_id,
              notebook_id: result.notebook_id,
            })
            .catch((error) => console.warn('Initial user profile generation failed.', error))
        }
      } catch {
        if (isCurrent) {
          setLoadError('无法打开笔记本')
        }
      } finally {
        if (isCurrent) {
          setIsLoading(false)
        }
      }
    }

    void loadNotebook()

    return () => {
      isCurrent = false
    }
  }, [notebookId, userId])

  if (!notebookId) {
    return (
      <div className="notebook-route-state is-error">
        <p>无法打开笔记本</p>
        <Link to="/">返回我的笔记本</Link>
      </div>
    )
  }

  if (isLoading) {
    return <div className="notebook-route-state">正在加载笔记本...</div>
  }

  if (!notebook) {
    return (
      <div className="notebook-route-state is-error">
        <p>{loadError}</p>
        <Link to="/">返回我的笔记本</Link>
      </div>
    )
  }

  return (
    <div
      className={`app-shell${isSidebarCollapsed ? ' is-sidebar-collapsed' : ''}${isClassroom ? ' is-classroom' : ''}${isTopbarHidden ? ' is-topbar-hidden' : ''}`}
    >
      <Sidebar
        notebookId={notebookId}
        isCollapsed={isSidebarCollapsed}
        onToggleSidebar={() => setIsSidebarCollapsed((current) => !current)}
      />
      <div className="app-main">
        {isTopbarHidden ? null : (
          <header className="topbar">
            <div className="topbar-title">
              <h1>{activeItem.label}</h1>
            </div>
            <div className="topbar-actions">
              <AccountMenu />
            </div>
          </header>
        )}
        <main className="page-surface">
          <NotebookVisit key={notebookId} notebook={notebook} />
        </main>
      </div>
    </div>
  )
}

export default AppLayout
