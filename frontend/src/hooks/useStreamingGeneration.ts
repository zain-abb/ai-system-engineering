import { useState, useCallback, useRef } from 'react'

export type ProcessingStep =
  | 'intent_classification'
  | 'semantic_search'
  | 'reranking'
  | 'llm_generation'
  | 'post_processing'

export type StepStatusType = 'pending' | 'running' | 'complete' | 'error'

export interface StepStatus {
  step: ProcessingStep
  status: StepStatusType
  message: string
  duration_ms?: number
  data?: Record<string, unknown>
}

export interface StreamingResult<TResponse> {
  success: boolean
  result: string
  usage?: Record<string, unknown>
  capability_used?: string
  error?: string
  raw?: TResponse
}

interface StreamEvent {
  type: 'step_start' | 'step_complete' | 'step_progress' | 'error' | 'done'
  step: ProcessingStep | null
  data: Record<string, unknown>
  timestamp: number
}

interface UseStreamingGenerationReturn<TRequest, TResponse> {
  isStreaming: boolean
  steps: Map<ProcessingStep, StepStatus>
  currentStep: ProcessingStep | null
  result: StreamingResult<TResponse> | null
  error: string | null
  startGeneration: (request: TRequest) => Promise<void>
  cancel: () => void
  reset: () => void
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useStreamingGeneration<TRequest, TResponse = unknown>(
  endpoint: string
): UseStreamingGenerationReturn<TRequest, TResponse> {
  const [isStreaming, setIsStreaming] = useState(false)
  const [steps, setSteps] = useState<Map<ProcessingStep, StepStatus>>(new Map())
  const [currentStep, setCurrentStep] = useState<ProcessingStep | null>(null)
  const [result, setResult] = useState<StreamingResult<TResponse> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    setSteps(new Map())
    setCurrentStep(null)
    setResult(null)
    setError(null)
    setIsStreaming(false)
  }, [])

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
  }, [])

  const parseSSEEvent = (text: string): { eventType: string; data: unknown } | null => {
    const lines = text.trim().split('\n')
    let eventType = ''
    let dataStr = ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7)
      } else if (line.startsWith('data: ')) {
        dataStr = line.slice(6)
      }
    }

    if (!eventType || !dataStr) {
      return null
    }

    try {
      return { eventType, data: JSON.parse(dataStr) }
    } catch {
      return null
    }
  }

  const startGeneration = useCallback(async (request: TRequest) => {
    // Reset state
    reset()
    setIsStreaming(true)

    // Create abort controller
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body is not readable')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })

        // Process complete events (separated by double newlines)
        const events = buffer.split('\n\n')
        buffer = events.pop() || '' // Keep incomplete event in buffer

        for (const eventText of events) {
          if (!eventText.trim()) continue

          const parsed = parseSSEEvent(eventText)
          if (!parsed) continue

          const { eventType, data } = parsed
          const eventData = data as StreamEvent | Record<string, unknown>

          switch (eventType) {
            case 'step_start': {
              const event = eventData as StreamEvent
              if (event.step) {
                const stepData = event.data as Record<string, unknown> | undefined
                const message = (stepData?.message as string) || 'Processing...'
                setCurrentStep(event.step)
                setSteps((prev) => {
                  const next = new Map(prev)
                  next.set(event.step!, {
                    step: event.step!,
                    status: 'running',
                    message,
                    data: stepData,
                  })
                  return next
                })
              }
              break
            }

            case 'step_complete': {
              const event = eventData as StreamEvent
              if (event.step) {
                const stepData = event.data as Record<string, unknown> | undefined
                const message = (stepData?.message as string) || 'Complete'
                const duration_ms = stepData?.duration_ms as number | undefined
                setSteps((prev) => {
                  const next = new Map(prev)
                  next.set(event.step!, {
                    step: event.step!,
                    status: 'complete',
                    message,
                    duration_ms,
                    data: stepData,
                  })
                  return next
                })
              }
              break
            }

            case 'step_progress': {
              const event = eventData as StreamEvent
              if (event.step) {
                const stepData = event.data as Record<string, unknown> | undefined
                setSteps((prev) => {
                  const next = new Map(prev)
                  const existing = next.get(event.step!)
                  const message = (stepData?.message as string) || existing?.message || 'Processing...'
                  next.set(event.step!, {
                    step: event.step!,
                    status: 'running',
                    message,
                    data: { ...existing?.data, ...stepData },
                  })
                  return next
                })
              }
              break
            }

            case 'error': {
              const errorMsg = (eventData as StreamEvent).data?.message as string || 'An error occurred'
              setError(errorMsg)
              const step = (eventData as StreamEvent).step
              if (step) {
                setSteps((prev) => {
                  const next = new Map(prev)
                  next.set(step, {
                    step,
                    status: 'error',
                    message: errorMsg,
                  })
                  return next
                })
              }
              break
            }

            case 'done': {
              const doneData = eventData as Record<string, unknown>
              setCurrentStep(null)
              setResult({
                success: doneData.success as boolean ?? true,
                result: doneData.result as string || '',
                usage: doneData.usage as Record<string, unknown> | undefined,
                capability_used: doneData.capability_used as string | undefined,
                error: doneData.error as string | undefined,
                raw: doneData as TResponse,
              })
              break
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was cancelled, don't treat as error
        return
      }
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(errorMessage)
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }, [endpoint, reset])

  return {
    isStreaming,
    steps,
    currentStep,
    result,
    error,
    startGeneration,
    cancel,
    reset,
  }
}
