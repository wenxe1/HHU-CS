import {
  Activity,
  Brain,
  CheckCircle2,
  Layers3,
  Loader2,
  MessageCircle,
  Radar,
  RefreshCw,
  Sparkles,
  Target,
  TriangleAlert,
  UserRound,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext } from 'react-router'
import {
  classroomApi,
  type NotebookSummary,
  type UserProfileRadarMetric,
  type UserProfileRecommendation,
  type UserProfileResult,
} from '../lib/api'
import { getActiveUserId } from '../lib/auth'

const RADAR_SIZE = 420
const RADAR_CENTER = RADAR_SIZE / 2
const RADAR_RADIUS = 132
const RADAR_LEVELS = 6

function toErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '请求失败'
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}

function formatGeneratedAt(value: string) {
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

function radarPoint(index: number, total: number, radius: number) {
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / total
  return {
    x: RADAR_CENTER + Math.cos(angle) * radius,
    y: RADAR_CENTER + Math.sin(angle) * radius,
  }
}

function pointsToString(points: Array<{ x: number; y: number }>) {
  return points.map((point) => `${point.x},${point.y}`).join(' ')
}

function RadarChart({ metrics }: { metrics: UserProfileRadarMetric[] }) {
  const axisCount = Math.max(metrics.length, 1)
  const gridPolygons = Array.from({ length: RADAR_LEVELS }, (_, index) => {
    const radius = (RADAR_RADIUS * (index + 1)) / RADAR_LEVELS
    return pointsToString(
      metrics.map((_, metricIndex) => radarPoint(metricIndex, axisCount, radius)),
    )
  })
  const valuePoints = pointsToString(
    metrics.map((metric, index) =>
      radarPoint(index, axisCount, RADAR_RADIUS * (Math.max(0, Math.min(100, metric.score)) / 100)),
    ),
  )

  return (
    <div className="user-profile-radar-wrap">
      <svg
        className="user-profile-radar"
        viewBox={`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`}
        role="img"
        aria-label="用户画像雷达图"
      >
        <defs>
          <radialGradient id="profileRadarGlow" cx="50%" cy="45%" r="62%">
            <stop offset="0%" stopColor="#dff4f1" stopOpacity="0.92" />
            <stop offset="58%" stopColor="#dbeafe" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="profileRadarFill" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0f9f8a" stopOpacity="0.72" />
            <stop offset="55%" stopColor="#2d72d9" stopOpacity="0.42" />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.3" />
          </linearGradient>
        </defs>
        <circle cx={RADAR_CENTER} cy={RADAR_CENTER} r={RADAR_RADIUS + 40} fill="url(#profileRadarGlow)" />
        {gridPolygons.map((points, index) => (
          <polygon
            className="user-profile-radar-grid"
            points={points}
            key={points}
            opacity={0.34 + index * 0.1}
          />
        ))}
        {metrics.map((metric, index) => {
          const edge = radarPoint(index, axisCount, RADAR_RADIUS)
          const label = radarPoint(index, axisCount, RADAR_RADIUS + 55)
          return (
            <g key={metric.key}>
              <line
                className="user-profile-radar-axis"
                x1={RADAR_CENTER}
                y1={RADAR_CENTER}
                x2={edge.x}
                y2={edge.y}
              />
              <text
                className="user-profile-radar-label"
                x={label.x}
                y={label.y}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                <tspan className="user-profile-radar-label-name" x={label.x} dy="-0.25em">
                  {metric.label}
                </tspan>
                <tspan className="user-profile-radar-label-score" x={label.x} dy="1.25em">
                  {metric.score}分
                </tspan>
              </text>
            </g>
          )
        })}
        <polygon className="user-profile-radar-fill" points={valuePoints} />
        <polygon className="user-profile-radar-line" points={valuePoints} />
        <circle className="user-profile-radar-center" cx={RADAR_CENTER} cy={RADAR_CENTER} r="2.6" />
        {metrics.map((metric, index) => {
          const score = Math.max(0, Math.min(100, metric.score))
          const point = radarPoint(index, axisCount, RADAR_RADIUS * (score / 100))
          return (
            <g key={`${metric.key}-score`}>
              <circle className="user-profile-radar-dot" cx={point.x} cy={point.y} r="5.5" />
              <title>{`${metric.label}: ${metric.score}`}</title>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function RecommendationItem({
  item,
  index,
}: {
  item: UserProfileRecommendation
  index: number
}) {
  const priorityLabel =
    item.priority === 'high' ? '优先' : item.priority === 'low' ? '轻量' : '建议'
  return (
    <article className={`user-profile-recommendation is-${item.priority || 'medium'}`}>
      <span>{index + 1}</span>
      <div>
        <strong>{item.title}</strong>
        <p>{item.detail}</p>
      </div>
      <em>{priorityLabel}</em>
    </article>
  )
}

function LockedProfile({
  profile,
  notebook,
}: {
  profile: UserProfileResult | null
  notebook: NotebookSummary
}) {
  const basePath = `/notebooks/${encodeURIComponent(notebook.notebook_id)}`
  return (
    <section className="user-profile-locked">
      <div className="user-profile-locked-visual">
        <Radar size={42} strokeWidth={1.7} />
      </div>
      <div className="user-profile-locked-copy">
        <span>画像未解锁</span>
        <h1>用户画像</h1>
        <p>
          {profile?.summary ||
            '还没有足够的学习记录生成画像。完成一次对话、测验或闪卡复习后会自动生成。'}
        </p>
      </div>
      <div className="user-profile-unlock-grid">
        <Link to={`${basePath}/classroom`}>
          <MessageCircle size={19} strokeWidth={2} />
          <span>互动课堂</span>
        </Link>
        <Link to={`${basePath}/tutor`}>
          <Brain size={19} strokeWidth={2} />
          <span>智能辅导</span>
        </Link>
        <Link to={`${basePath}/resources`}>
          <Layers3 size={19} strokeWidth={2} />
          <span>资源中心</span>
        </Link>
      </div>
    </section>
  )
}

function UserProfile() {
  const notebook = useOutletContext<NotebookSummary | null>()
  const userId = getActiveUserId()
  const [profile, setProfile] = useState<UserProfileResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const metrics = profile?.radar ?? []
  const topMetric = useMemo(
    () =>
      metrics.length > 0
        ? [...metrics].sort((left, right) => right.score - left.score)[0]
        : null,
    [metrics],
  )

  const loadProfile = useCallback(async (forceRefresh = false) => {
    if (!notebook) {
      return
    }
    setIsLoading(true)
    setErrorMessage('')
    try {
      const result = forceRefresh
        ? await classroomApi.generateProfile({
            user_id: userId,
            course_id: notebook.course_id,
            notebook_id: notebook.notebook_id,
            force_refresh: true,
          })
        : await classroomApi.profile({
            user_id: userId,
            course_id: notebook.course_id,
            notebook_id: notebook.notebook_id,
          })
      setProfile(result)
    } catch (error) {
      setErrorMessage(
        forceRefresh
          ? `画像生成失败：${toErrorMessage(error)}`
          : `画像读取失败：${toErrorMessage(error)}`,
      )
    } finally {
      setIsLoading(false)
    }
  }, [notebook, userId])

  useEffect(() => {
    void loadProfile()
  }, [loadProfile])

  if (!notebook) {
    return (
      <div className="user-profile-page">
        <section className="user-profile-state">无法打开当前笔记本。</section>
      </div>
    )
  }

  return (
    <div className="user-profile-page">
      <header className="user-profile-header">
        <div className="user-profile-title">
          <span>
            <UserRound size={16} strokeWidth={2} />
            {notebook.title}
          </span>
          <h1>用户画像</h1>
        </div>
        <button type="button" onClick={() => void loadProfile(true)} disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="user-profile-spin" size={17} strokeWidth={2} />
          ) : (
            <RefreshCw size={17} strokeWidth={2} />
          )}
          重新生成
        </button>
      </header>

      {errorMessage ? (
        <div className="user-profile-error">
          <TriangleAlert size={18} strokeWidth={2} />
          {errorMessage}
        </div>
      ) : null}

      {isLoading && !profile ? (
        <section className="user-profile-state">
          <Loader2 className="user-profile-spin" size={26} strokeWidth={1.9} />
          正在读取用户画像...
        </section>
      ) : profile && !profile.is_unlocked ? (
        <LockedProfile profile={profile} notebook={notebook} />
      ) : profile ? (
        <div className="user-profile-grid">
          <section className="user-profile-radar-panel">
            <div className="user-profile-panel-head">
              <div>
                <span>学习能力雷达</span>
                <h2>{topMetric ? `${topMetric.label}表现最突出` : '近期表现'}</h2>
              </div>
              <strong>{formatGeneratedAt(profile.generated_at)}</strong>
            </div>
            <RadarChart metrics={metrics} />
          </section>

          <section className="user-profile-summary-panel">
            <div className="user-profile-summary">
              <Sparkles size={20} strokeWidth={1.9} />
              <p>{profile.summary}</p>
            </div>

            <div className="user-profile-stat-grid">
              <article>
                <MessageCircle size={18} strokeWidth={2} />
                <span>对话</span>
                <strong>{profile.signals.conversation_count}</strong>
              </article>
              <article>
                <Target size={18} strokeWidth={2} />
                <span>测验</span>
                <strong>{profile.signals.quiz_attempt_count}</strong>
              </article>
              <article>
                <Activity size={18} strokeWidth={2} />
                <span>闪卡</span>
                <strong>{profile.signals.flashcard_attempt_count}</strong>
              </article>
              <article>
                <CheckCircle2 size={18} strokeWidth={2} />
                <span>正确率</span>
                <strong>
                  {formatPercent(
                    Math.max(profile.signals.quiz_accuracy, profile.signals.flashcard_accuracy),
                  )}
                </strong>
              </article>
            </div>

            {profile.learning_traits.length > 0 ? (
              <div className="user-profile-traits">
                {profile.learning_traits.map((trait) => (
                  <span key={trait}>{trait}</span>
                ))}
              </div>
            ) : null}

            <div className="user-profile-metric-list">
              {metrics.map((metric) => (
                <article key={metric.key}>
                  <div>
                    <strong>{metric.label}</strong>
                    <span>{metric.reason}</span>
                  </div>
                  <em>{metric.score}</em>
                </article>
              ))}
            </div>

            <div className="user-profile-insight-grid">
              <section>
                <h2>优势</h2>
                {profile.strengths.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </section>
              <section>
                <h2>风险</h2>
                {profile.risks.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </section>
            </div>

            <section className="user-profile-recommendations">
              <div className="user-profile-panel-head">
                <div>
                  <span>学习建议</span>
                  <h2>下一步</h2>
                </div>
              </div>
              {profile.recommendations.map((item, index) => (
                <RecommendationItem item={item} index={index} key={`${item.title}-${index}`} />
              ))}
            </section>
          </section>
        </div>
      ) : (
        <section className="user-profile-state">
          <Radar size={26} strokeWidth={1.9} />
          暂无画像数据。
        </section>
      )}
    </div>
  )
}

export default UserProfile
