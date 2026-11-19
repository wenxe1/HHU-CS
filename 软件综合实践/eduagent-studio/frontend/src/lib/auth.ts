const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE_URL = (rawApiBaseUrl ?? '').replace(/\/$/, '')
const AUTH_STORAGE_KEY = 'isLoggedIn'
const USER_NAME_STORAGE_KEY = 'authUserName'
const USER_ID_STORAGE_KEY = 'authUserId'
const AUTH_NOTICE_STORAGE_KEY = 'authNotice'

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

interface AuthUser {
  user_id: string
  username: string
}

type AuthResult =
  | { ok: true; message: string; user: AuthUser }
  | { ok: false; message: string }

export function isLoggedIn() {
  return window.localStorage.getItem(AUTH_STORAGE_KEY) === 'true'
}

export function setLoggedIn(userName: string, userId = '') {
  window.localStorage.setItem(AUTH_STORAGE_KEY, 'true')
  window.localStorage.setItem(USER_NAME_STORAGE_KEY, userName)
  if (userId.length > 0) {
    window.localStorage.setItem(USER_ID_STORAGE_KEY, userId)
  }
}

export function clearLogin() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY)
  window.localStorage.removeItem(USER_NAME_STORAGE_KEY)
  window.localStorage.removeItem(USER_ID_STORAGE_KEY)
}

export function getUserName() {
  return window.localStorage.getItem(USER_NAME_STORAGE_KEY) ?? '用户中心'
}

export function getUserId() {
  return window.localStorage.getItem(USER_ID_STORAGE_KEY) ?? ''
}

export function getActiveUserId() {
  return getUserId() || getUserName()
}

export function getUserInitials(userName = getUserName()) {
  const normalizedName = userName.trim()

  if (normalizedName.length === 0) {
    return 'EA'
  }

  const latinParts = normalizedName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  if (/^[A-Z]{1,2}$/.test(latinParts)) {
    return latinParts
  }

  return normalizedName.slice(0, 2).toUpperCase()
}

export async function registerUser(
  username: string,
  password: string,
  confirmPassword: string,
): Promise<AuthResult> {
  const normalizedUsername = username.trim()
  const normalizedPassword = password.trim()
  const normalizedConfirmPassword = confirmPassword.trim()

  if (normalizedUsername.length === 0) {
    return { ok: false, message: '请输入用户名' }
  }

  if (normalizedPassword.length === 0) {
    return { ok: false, message: '请输入密码' }
  }

  if (normalizedConfirmPassword.length === 0) {
    return { ok: false, message: '请输入确认密码' }
  }

  if (normalizedPassword !== normalizedConfirmPassword) {
    return { ok: false, message: '两次输入的密码不一致' }
  }

  return postAuth('/api/auth/register', {
    username: normalizedUsername,
    password: normalizedPassword,
    confirm_password: normalizedConfirmPassword,
  })
}

export async function loginUser(username: string, password: string): Promise<AuthResult> {
  const normalizedUsername = username.trim()
  const normalizedPassword = password.trim()

  if (normalizedUsername.length === 0) {
    return { ok: false, message: '请输入用户名' }
  }

  if (normalizedPassword.length === 0) {
    return { ok: false, message: '请输入密码' }
  }

  const result = await postAuth('/api/auth/login', {
    username: normalizedUsername,
    password: normalizedPassword,
  })

  if (result.ok) {
    setLoggedIn(result.user.username, result.user.user_id)
  }

  return result
}

export function setAuthNotice(message: string) {
  window.localStorage.setItem(AUTH_NOTICE_STORAGE_KEY, message)
}

export function consumeAuthNotice() {
  const message = window.localStorage.getItem(AUTH_NOTICE_STORAGE_KEY)
  window.localStorage.removeItem(AUTH_NOTICE_STORAGE_KEY)
  return message ?? ''
}

async function postAuth(path: string, body: unknown): Promise<AuthResult> {
  try {
    const response = await fetch(resolveAuthUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const payload = (await response.json()) as ApiResponse<AuthUser>

    if (!response.ok || payload.code !== 0) {
      return { ok: false, message: toUserMessage(payload.message) }
    }

    return { ok: true, message: 'success', user: payload.data }
  } catch {
    return { ok: false, message: '无法连接后端服务' }
  }
}

function resolveAuthUrl(pathOrUrl: string) {
  if (/^https?:/i.test(pathOrUrl)) {
    return pathOrUrl
  }

  const path = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path
}

function toUserMessage(message: string) {
  if (message === 'username already exists') {
    return '该用户名已存在'
  }
  if (message === 'invalid username or password') {
    return '账号或密码错误'
  }
  if (message === 'password confirmation does not match') {
    return '两次输入的密码不一致'
  }
  return message || '请求失败'
}
