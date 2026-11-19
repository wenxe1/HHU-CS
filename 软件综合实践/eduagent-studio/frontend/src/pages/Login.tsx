import { type FormEvent, useEffect, useState } from 'react'
import { ArrowRight, LockKeyhole, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import loginHero from '../assets/login-hero.png'
import { consumeAuthNotice, isLoggedIn, loginUser } from '../lib/auth'

function Login() {
  const navigate = useNavigate()
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState('')
  const [formNotice, setFormNotice] = useState(() => consumeAuthNotice())
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isLoggedIn()) {
      navigate('/', { replace: true })
      return
    }
  }, [navigate])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)

    const result = await loginUser(userName, password)

    if (!result.ok) {
      setFormError(result.message)
      setIsSubmitting(false)
      return
    }

    navigate('/', { replace: true })
  }

  return (
    <main className="login-page">
      <section className="login-visual is-clean" aria-label="EduAgent Studio 学习场景">
        <img className="login-hero-image" src={loginHero} alt="EduAgent Studio 学习平台主视觉" />
        <div className="login-brand-row">
          <img className="brand-logo" src="/favicon.svg" alt="" />
          <strong>EduAgent Studio</strong>
        </div>
      </section>

      <section className="login-form-panel" aria-label="登录表单">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-form-title">
            <h2>登录 EduAgent Studio</h2>
          </div>

          <label className="login-field">
            <span>用户名</span>
            <div>
              <UserRound size={18} strokeWidth={1.9} />
              <input
                value={userName}
                onChange={(event) => {
                  setUserName(event.target.value)
                  setFormError('')
                  setFormNotice('')
                }}
                placeholder="请输入用户名"
                autoComplete="username"
              />
            </div>
          </label>

          <label className="login-field">
            <span>密码</span>
            <div>
              <LockKeyhole size={18} strokeWidth={1.9} />
              <input
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  setFormError('')
                  setFormNotice('')
                }}
                placeholder="请输入密码"
                type="password"
                autoComplete="current-password"
              />
            </div>
          </label>

          {formNotice.length > 0 ? <p className="login-notice">{formNotice}</p> : null}
          {formError.length > 0 ? <p className="login-error">{formError}</p> : null}

          <button className="login-submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? '登录中' : '登录'}
            <ArrowRight size={18} strokeWidth={2} />
          </button>

          <div className="auth-switch-row">
            <span>还没有账号？</span>
            <Link to="/register">注册账号</Link>
          </div>
        </form>
      </section>
    </main>
  )
}

export default Login
