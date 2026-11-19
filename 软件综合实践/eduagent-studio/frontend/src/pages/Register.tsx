import { type FormEvent, useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2, LockKeyhole, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import loginHero from '../assets/login-hero.png'
import { isLoggedIn, registerUser, setAuthNotice } from '../lib/auth'

function Register() {
  const navigate = useNavigate()
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formError, setFormError] = useState('')
  const [formNotice, setFormNotice] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isLoggedIn()) {
      navigate('/', { replace: true })
    }
  }, [navigate])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    const result = await registerUser(userName, password, confirmPassword)

    if (!result.ok) {
      setFormNotice('')
      setFormError(result.message)
      setIsSubmitting(false)
      return
    }

    setFormError('')
    setFormNotice('注册成功，请登录')
    setAuthNotice('注册成功，请登录')
    window.setTimeout(() => {
      navigate('/login', { replace: true })
    }, 450)
  }

  function clearFeedback() {
    setFormError('')
    setFormNotice('')
  }

  return (
    <main className="login-page register-page">
      <section className="login-visual" aria-label="EduAgent Studio 学习场景">
        <img className="login-hero-image" src={loginHero} alt="EduAgent Studio 学习平台主视觉" />
        <div className="login-brand-row">
          <img className="brand-logo" src="/favicon.svg" alt="" />
          <strong>EduAgent Studio</strong>
        </div>

        <div className="login-visual-copy">
          <h1>创建你的学习工作台账号</h1>
          <p>注册后即可进入学习画像、资源推荐和智能辅导的前端演示流程。</p>
        </div>

        <div className="login-feature-grid" aria-label="平台能力">
          <article>
            <CheckCircle2 size={18} strokeWidth={2} />
            <span>学习画像</span>
          </article>
          <article>
            <CheckCircle2 size={18} strokeWidth={2} />
            <span>资源推荐</span>
          </article>
          <article>
            <CheckCircle2 size={18} strokeWidth={2} />
            <span>智能辅导</span>
          </article>
        </div>
      </section>

      <section className="login-form-panel" aria-label="注册表单">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-form-title">
            <Link className="back-login-link" to="/login">
              <ArrowLeft size={16} strokeWidth={2} />
              返回登录
            </Link>
            <h2>注册账号</h2>
          </div>

          <label className="login-field">
            <span>用户名</span>
            <div>
              <UserRound size={18} strokeWidth={1.9} />
              <input
                value={userName}
                onChange={(event) => {
                  setUserName(event.target.value)
                  clearFeedback()
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
                  clearFeedback()
                }}
                placeholder="请输入密码"
                type="password"
                autoComplete="new-password"
              />
            </div>
          </label>

          <label className="login-field">
            <span>确认密码</span>
            <div>
              <LockKeyhole size={18} strokeWidth={1.9} />
              <input
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value)
                  clearFeedback()
                }}
                placeholder="请再次输入密码"
                type="password"
                autoComplete="new-password"
              />
            </div>
          </label>

          {formNotice.length > 0 ? <p className="login-notice">{formNotice}</p> : null}
          {formError.length > 0 ? <p className="login-error">{formError}</p> : null}

          <button className="login-submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? '注册中' : '注册'}
            <ArrowRight size={18} strokeWidth={2} />
          </button>

          <div className="auth-switch-row">
            <span>已有账号？</span>
            <Link to="/login">立即登录</Link>
          </div>
        </form>
      </section>
    </main>
  )
}

export default Register
