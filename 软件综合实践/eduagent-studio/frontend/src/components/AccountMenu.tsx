import { useEffect, useRef, useState } from 'react'
import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router'
import { clearLogin, getUserInitials, getUserName } from '../lib/auth'

interface AccountMenuProps {
  compact?: boolean
}

function AccountMenu({ compact = false }: AccountMenuProps) {
  const navigate = useNavigate()
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const userName = getUserName()
  const userInitials = getUserInitials(userName)

  function clearCloseTimer() {
    if (closeTimerRef.current !== null) {
      clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
  }

  function handleOpen() {
    clearCloseTimer()
    setIsOpen(true)
  }

  function handleCloseWithDelay() {
    clearCloseTimer()
    closeTimerRef.current = setTimeout(() => {
      setIsOpen(false)
      closeTimerRef.current = null
    }, 150)
  }

  function handleLogout() {
    clearCloseTimer()
    clearLogin()
    navigate('/login', { replace: true })
  }

  useEffect(() => clearCloseTimer, [])

  return (
    <div
      className={`account-menu${isOpen ? ' is-open' : ''}${compact ? ' is-compact' : ''}`}
      onMouseEnter={handleOpen}
      onMouseLeave={handleCloseWithDelay}
    >
      <button
        className={`account-entry${compact ? ' is-compact' : ''}`}
        type="button"
        aria-label="用户中心"
        aria-expanded={isOpen}
      >
        <span className="account-avatar">{userInitials}</span>
        {!compact ? (
          <span className="account-copy">
            <strong>{userName}</strong>
            <small>已登录</small>
          </span>
        ) : null}
      </button>

      <div className="account-popover" role="menu" aria-label="用户菜单">
        <div className="account-popover-head">
          <span className="account-avatar">{userInitials}</span>
          <div>
            <strong>{userName}</strong>
            <small>已登录</small>
          </div>
        </div>
        <button className="logout-action" type="button" role="menuitem" onClick={handleLogout}>
          <LogOut size={17} strokeWidth={2} />
          退出登录
        </button>
      </div>
    </div>
  )
}

export default AccountMenu
