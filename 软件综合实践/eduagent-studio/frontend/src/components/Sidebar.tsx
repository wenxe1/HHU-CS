import { Link, NavLink } from 'react-router'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { navigationItems } from '../data/navigation'

interface SidebarProps {
  notebookId: string
  isCollapsed: boolean
  onToggleSidebar: () => void
}

function Sidebar({ notebookId, isCollapsed, onToggleSidebar }: SidebarProps) {
  const ToggleIcon = isCollapsed ? PanelLeftOpen : PanelLeftClose
  const resolveNotebookPath = (path: string) =>
    notebookId ? `/notebooks/${encodeURIComponent(notebookId)}/${path}` : path

  return (
    <aside className={`sidebar${isCollapsed ? ' is-collapsed' : ''}`} aria-label="主导航">
      <div className="sidebar-head">
        <Link className="brand-block" to="/" aria-label="返回笔记本主页">
          <img className="brand-logo" src="/favicon.svg" alt="" />
          <div className="brand-copy">
            <strong>EduAgent Studio</strong>
          </div>
        </Link>
        <button
          className="sidebar-toggle"
          type="button"
          onClick={onToggleSidebar}
          aria-label={isCollapsed ? '打开侧边栏' : '收起侧边栏'}
          aria-expanded={!isCollapsed}
        >
          <ToggleIcon size={21} strokeWidth={1.9} />
        </button>
      </div>

      <nav className="nav-list">
        {navigationItems.map((item) => {
          const Icon = item.icon

          return (
            <NavLink
              key={item.path}
              to={resolveNotebookPath(item.path)}
              end={item.path === 'classroom'}
              className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}
              title={item.label}
            >
              <span className="nav-icon-shell" aria-hidden="true">
                <Icon className="nav-icon" size={19} strokeWidth={2} />
              </span>
              <span className="nav-copy">
                <strong>{item.label}</strong>
              </span>
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}

export default Sidebar
