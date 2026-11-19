import { useState, type ReactNode } from 'react'
import {
  NotebookSessionContext,
  type NotebookSessionStore,
} from './NotebookSessionContext'

export function NotebookSessionProvider({
  children,
  visitId,
}: {
  children: ReactNode
  visitId: string
}) {
  const [store] = useState<NotebookSessionStore>(() => ({
    visitId,
    values: new Map(),
    listeners: new Map(),
  }))

  return (
    <NotebookSessionContext.Provider value={store}>
      {children}
    </NotebookSessionContext.Provider>
  )
}
