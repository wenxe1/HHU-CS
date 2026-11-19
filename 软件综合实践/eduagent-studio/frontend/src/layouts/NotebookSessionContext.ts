import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react'

export type SessionListener = (value: unknown) => void

export interface NotebookSessionStore {
  visitId: string
  values: Map<string, unknown>
  listeners: Map<string, Set<SessionListener>>
}

export const NotebookSessionContext = createContext<NotebookSessionStore | null>(null)

export function useNotebookVisitId() {
  const store = useContext(NotebookSessionContext)
  if (!store) {
    throw new Error('useNotebookVisitId must be used inside NotebookSessionProvider')
  }
  return store.visitId
}

export function useNotebookSessionState<T>(
  key: string,
  initialValue: T | (() => T),
): [T, Dispatch<SetStateAction<T>>] {
  const store = useContext(NotebookSessionContext)
  if (!store) {
    throw new Error('useNotebookSessionState must be used inside NotebookSessionProvider')
  }

  if (!store.values.has(key)) {
    store.values.set(
      key,
      typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue,
    )
  }

  const [value, setValue] = useState<T>(() => store.values.get(key) as T)

  useEffect(() => {
    const listener: SessionListener = (nextValue) => setValue(nextValue as T)
    const listeners = store.listeners.get(key) ?? new Set<SessionListener>()
    listeners.add(listener)
    store.listeners.set(key, listeners)

    return () => {
      listeners.delete(listener)
      if (listeners.size === 0) {
        store.listeners.delete(key)
      }
    }
  }, [key, store])

  const setSessionValue = useCallback<Dispatch<SetStateAction<T>>>(
    (nextValue) => {
      const previousValue = store.values.get(key) as T
      const resolvedValue =
        typeof nextValue === 'function'
          ? (nextValue as (previous: T) => T)(previousValue)
          : nextValue
      store.values.set(key, resolvedValue)
      store.listeners.get(key)?.forEach((listener) => listener(resolvedValue))
    },
    [key, store],
  )

  return [value, setSessionValue]
}
