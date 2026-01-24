import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'

// Available Claude models
export const CLAUDE_MODELS = [
  { id: 'claude-3-5-haiku-20241022', name: 'Haiku', description: 'Fast & cost-effective' },
  { id: 'claude-sonnet-4-20250514', name: 'Sonnet', description: 'Balanced performance' },
  { id: 'claude-opus-4-20250514', name: 'Opus', description: 'Highest quality' },
] as const

export type ModelId = typeof CLAUDE_MODELS[number]['id']

const DEFAULT_MODEL: ModelId = 'claude-3-5-haiku-20241022'
const STORAGE_KEY = 'se-agent-model'

interface SettingsContextType {
  model: ModelId
  setModel: (model: ModelId) => void
  getModelInfo: () => typeof CLAUDE_MODELS[number]
}

const SettingsContext = createContext<SettingsContextType | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [model, setModelState] = useState<ModelId>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && CLAUDE_MODELS.some(m => m.id === stored)) {
      return stored as ModelId
    }
    return DEFAULT_MODEL
  })

  // Persist to localStorage when model changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, model)
  }, [model])

  const setModel = useCallback((newModel: ModelId) => {
    setModelState(newModel)
  }, [])

  const getModelInfo = useCallback(() => {
    return CLAUDE_MODELS.find(m => m.id === model) || CLAUDE_MODELS[0]
  }, [model])

  return (
    <SettingsContext.Provider value={{ model, setModel, getModelInfo }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
