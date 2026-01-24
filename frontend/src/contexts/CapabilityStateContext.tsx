import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import type { ProcessingStep, StepStatus, StreamingResult } from '@/hooks/useStreamingGeneration'

// State for each capability page
export interface CodeGenerationState {
  requirements: string
  language: string
  context: string
  result: StreamingResult<unknown> | null
  steps: Map<ProcessingStep, StepStatus>
}

export interface TestGenerationState {
  code: string
  language: string
  framework: string
  result: StreamingResult<unknown> | null
  steps: Map<ProcessingStep, StepStatus>
}

export interface CodeReviewState {
  code: string
  language: string
  focus: string
  result: StreamingResult<unknown> | null
  steps: Map<ProcessingStep, StepStatus>
}

export interface DocumentationState {
  code: string
  language: string
  docType: string
  result: StreamingResult<unknown> | null
  steps: Map<ProcessingStep, StepStatus>
}

export interface RequirementsState {
  requirements: string
  context: string
  result: StreamingResult<unknown> | null
  steps: Map<ProcessingStep, StepStatus>
}

interface CapabilityStateContextType {
  // Code Generation
  codeGeneration: CodeGenerationState
  setCodeGeneration: (state: Partial<CodeGenerationState>) => void
  resetCodeGeneration: () => void

  // Test Generation
  testGeneration: TestGenerationState
  setTestGeneration: (state: Partial<TestGenerationState>) => void
  resetTestGeneration: () => void

  // Code Review
  codeReview: CodeReviewState
  setCodeReview: (state: Partial<CodeReviewState>) => void
  resetCodeReview: () => void

  // Documentation
  documentation: DocumentationState
  setDocumentation: (state: Partial<DocumentationState>) => void
  resetDocumentation: () => void

  // Requirements
  requirements: RequirementsState
  setRequirements: (state: Partial<RequirementsState>) => void
  resetRequirements: () => void
}

const defaultCodeGenerationState: CodeGenerationState = {
  requirements: '',
  language: 'python',
  context: '',
  result: null,
  steps: new Map(),
}

const defaultTestGenerationState: TestGenerationState = {
  code: '',
  language: 'python',
  framework: 'pytest',
  result: null,
  steps: new Map(),
}

const defaultCodeReviewState: CodeReviewState = {
  code: '',
  language: 'python',
  focus: 'general',
  result: null,
  steps: new Map(),
}

const defaultDocumentationState: DocumentationState = {
  code: '',
  language: 'python',
  docType: 'API',
  result: null,
  steps: new Map(),
}

const defaultRequirementsState: RequirementsState = {
  requirements: '',
  context: '',
  result: null,
  steps: new Map(),
}

const CapabilityStateContext = createContext<CapabilityStateContextType | null>(null)

export function CapabilityStateProvider({ children }: { children: ReactNode }) {
  const [codeGeneration, setCodeGenerationState] = useState<CodeGenerationState>(defaultCodeGenerationState)
  const [testGeneration, setTestGenerationState] = useState<TestGenerationState>(defaultTestGenerationState)
  const [codeReview, setCodeReviewState] = useState<CodeReviewState>(defaultCodeReviewState)
  const [documentation, setDocumentationState] = useState<DocumentationState>(defaultDocumentationState)
  const [requirements, setRequirementsState] = useState<RequirementsState>(defaultRequirementsState)

  const setCodeGeneration = useCallback((state: Partial<CodeGenerationState>) => {
    setCodeGenerationState((prev) => ({ ...prev, ...state }))
  }, [])

  const resetCodeGeneration = useCallback(() => {
    setCodeGenerationState(defaultCodeGenerationState)
  }, [])

  const setTestGeneration = useCallback((state: Partial<TestGenerationState>) => {
    setTestGenerationState((prev) => ({ ...prev, ...state }))
  }, [])

  const resetTestGeneration = useCallback(() => {
    setTestGenerationState(defaultTestGenerationState)
  }, [])

  const setCodeReview = useCallback((state: Partial<CodeReviewState>) => {
    setCodeReviewState((prev) => ({ ...prev, ...state }))
  }, [])

  const resetCodeReview = useCallback(() => {
    setCodeReviewState(defaultCodeReviewState)
  }, [])

  const setDocumentation = useCallback((state: Partial<DocumentationState>) => {
    setDocumentationState((prev) => ({ ...prev, ...state }))
  }, [])

  const resetDocumentation = useCallback(() => {
    setDocumentationState(defaultDocumentationState)
  }, [])

  const setRequirements = useCallback((state: Partial<RequirementsState>) => {
    setRequirementsState((prev) => ({ ...prev, ...state }))
  }, [])

  const resetRequirements = useCallback(() => {
    setRequirementsState(defaultRequirementsState)
  }, [])

  return (
    <CapabilityStateContext.Provider
      value={{
        codeGeneration,
        setCodeGeneration,
        resetCodeGeneration,
        testGeneration,
        setTestGeneration,
        resetTestGeneration,
        codeReview,
        setCodeReview,
        resetCodeReview,
        documentation,
        setDocumentation,
        resetDocumentation,
        requirements,
        setRequirements,
        resetRequirements,
      }}
    >
      {children}
    </CapabilityStateContext.Provider>
  )
}

export function useCapabilityState() {
  const context = useContext(CapabilityStateContext)
  if (!context) {
    throw new Error('useCapabilityState must be used within a CapabilityStateProvider')
  }
  return context
}
