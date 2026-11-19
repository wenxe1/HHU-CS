import type { ComponentType } from 'react'

export type NavIcon = ComponentType<{
  className?: string
  size?: number
  strokeWidth?: number
}>

export interface NavigationItem {
  label: string
  path: string
  icon: NavIcon
}

export interface LearningGoal {
  course: string
  target: string
  horizon: string
  focus: string
  stage: string
  updatedAt: string
}

export interface LearningLoopStep {
  label: string
  state: 'done' | 'active' | 'pending'
  description: string
}

export interface LearningTask {
  id: string
  time: string
  title: string
  topic: string
  duration: string
  status: '待开始' | '进行中' | '已完成'
  intent: string
}

export type GeneratedResourceType = '讲义' | '题库' | '思维导图' | 'PPT' | '代码案例' | '互动课堂'

export type GeneratedResourceStatus = '待生成' | '生成中' | '已完成' | '待审核'

export interface GeneratedLearningResource {
  resource_id: string
  knowledge_point_id: string
  title: string
  type: GeneratedResourceType
  status: GeneratedResourceStatus
  progress: number
  created_at: string
  related_knowledge_point: string
  fit_reason: string
  source: string
  estimated_minutes: number
}

export interface ResourceRecommendation {
  id: string
  type: string
  title: string
  reason: string
  tags: string[]
}

export interface WeakKnowledgePoint {
  name: string
  score: number
  diagnosis: string
}

export interface WorkflowAction {
  title: string
  description: string
  path: string
  action: string
}

export interface PlaceholderPageContent {
  title: string
  summary: string
  goals: string[]
  nextMilestone: string
}
