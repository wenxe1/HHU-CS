import {
  BookOpenCheck,
  BotMessageSquare,
  FileText,
  Presentation,
  Radar,
} from 'lucide-react'
import type { NavigationItem } from '../types/learning'

export const navigationItems: NavigationItem[] = [
  {
    label: '互动课堂',
    path: 'classroom',
    icon: Presentation,
  },
  {
    label: '智能辅导',
    path: 'tutor',
    icon: BotMessageSquare,
  },
  {
    label: '资源中心',
    path: 'resources',
    icon: BookOpenCheck,
  },
  {
    label: '用户画像',
    path: 'profile',
    icon: Radar,
  },
]

export const supportLinks: NavigationItem[] = [
  {
    label: '资源审核',
    path: 'resources',
    icon: FileText,
  },
]
