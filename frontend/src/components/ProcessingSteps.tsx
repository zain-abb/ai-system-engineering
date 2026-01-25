import { useState } from 'react'
import { Check, Clock, Loader2, AlertCircle, ChevronDown, ChevronRight, FileCode } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ProcessingStep, StepStatus, StepStatusType } from '@/hooks/useStreamingGeneration'

const STEP_ORDER: ProcessingStep[] = [
  'intent_classification',
  'semantic_search',
  'reranking',
  'llm_generation',
  'post_processing',
]

const STEP_LABELS: Record<ProcessingStep, string> = {
  intent_classification: 'Analyzing Request',
  semantic_search: 'Searching Context',
  reranking: 'Ranking Results',
  llm_generation: 'Generating with Claude',
  post_processing: 'Finalizing',
}

const STEP_DESCRIPTIONS: Record<ProcessingStep, string> = {
  intent_classification: 'Understanding your request type',
  semantic_search: 'Finding relevant code and context',
  reranking: 'Prioritizing the best matches',
  llm_generation: 'Creating your response',
  post_processing: 'Cleaning up and formatting',
}

interface StepIconProps {
  status: StepStatusType
}

function StepIcon({ status }: StepIconProps) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
    case 'complete':
      return <Check className="h-5 w-5 text-green-500" />
    case 'error':
      return <AlertCircle className="h-5 w-5 text-red-500" />
    case 'pending':
    default:
      return <Clock className="h-5 w-5 text-muted-foreground opacity-50" />
  }
}

interface ExpandableFileListProps {
  files: unknown
}

function ExpandableFileList({ files }: ExpandableFileListProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!files || !Array.isArray(files) || files.length === 0) {
    return null
  }

  const fileList = files as string[]

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <span>View {fileList.length} source {fileList.length === 1 ? 'file' : 'files'}</span>
      </button>

      {isExpanded && (
        <div className="mt-1.5 pl-4 space-y-1">
          {fileList.map((filePath, index) => {
            const fileName = filePath.split('/').pop() || filePath
            // Get parent directory for context
            const parts = filePath.split('/')
            const parentDir = parts.length > 1 ? parts[parts.length - 2] : ''

            return (
              <div
                key={index}
                className="flex items-center gap-1.5 text-xs"
                title={filePath}
              >
                <FileCode className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                <span className="font-mono truncate">
                  {parentDir && <span className="text-muted-foreground">{parentDir}/</span>}
                  {fileName}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

interface ProcessingStepsProps {
  steps: Map<ProcessingStep, StepStatus>
  currentStep: ProcessingStep | null
  className?: string
  showAllSteps?: boolean
}

export function ProcessingSteps({
  steps,
  currentStep,
  className,
  showAllSteps = false,
}: ProcessingStepsProps) {
  // Determine which steps to show
  const visibleSteps = showAllSteps
    ? STEP_ORDER
    : STEP_ORDER.filter((step) => steps.has(step) || step === currentStep)

  if (visibleSteps.length === 0) {
    return null
  }

  return (
    <div className={cn('space-y-2', className)}>
      {visibleSteps.map((stepKey) => {
        const step = steps.get(stepKey)
        const status: StepStatusType = step?.status || 'pending'

        return (
          <div
            key={stepKey}
            className={cn(
              'flex items-center gap-3 p-3 rounded-lg border transition-all duration-200',
              status === 'running' && 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800',
              status === 'complete' && 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800',
              status === 'error' && 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800',
              status === 'pending' && 'bg-muted/30 border-muted opacity-60'
            )}
          >
            <StepIcon status={status} />

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    'font-medium text-sm',
                    status === 'running' && 'text-blue-700 dark:text-blue-300',
                    status === 'complete' && 'text-green-700 dark:text-green-300',
                    status === 'error' && 'text-red-700 dark:text-red-300',
                    status === 'pending' && 'text-muted-foreground'
                  )}
                >
                  {STEP_LABELS[stepKey]}
                </span>

                {step?.duration_ms !== undefined && (
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {step.duration_ms}ms
                  </span>
                )}
              </div>

              <p className="text-xs text-muted-foreground mt-0.5 truncate">
                {step?.message || (step?.data?.message as string | undefined) || STEP_DESCRIPTIONS[stepKey]}
              </p>

              {/* Show additional data for certain steps */}
              {step?.data && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {step.data.confidence !== undefined && (
                    <span className="text-xs bg-background px-1.5 py-0.5 rounded border">
                      Confidence: {(step.data.confidence as number * 100).toFixed(0)}%
                    </span>
                  )}
                  {step.data.candidates_found !== undefined && (
                    <span className="text-xs bg-background px-1.5 py-0.5 rounded border">
                      Found: {step.data.candidates_found as number} files
                    </span>
                  )}
                  {step.data.output_tokens !== undefined && (
                    <span className="text-xs bg-background px-1.5 py-0.5 rounded border">
                      Tokens: {step.data.output_tokens as number}
                    </span>
                  )}
                </div>
              )}

              {/* Show expandable file list for semantic search */}
              <ExpandableFileList files={step?.data?.files} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// Compact version for smaller spaces
export function ProcessingStepsCompact({
  steps,
  currentStep,
  className,
}: Omit<ProcessingStepsProps, 'showAllSteps'>) {
  const activeSteps = STEP_ORDER.filter((step) => steps.has(step))

  if (activeSteps.length === 0 && !currentStep) {
    return null
  }

  const current = steps.get(currentStep as ProcessingStep)

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Step indicators */}
      <div className="flex gap-1">
        {STEP_ORDER.map((stepKey) => {
          const step = steps.get(stepKey)
          const status: StepStatusType = step?.status || 'pending'

          return (
            <div
              key={stepKey}
              className={cn(
                'w-2 h-2 rounded-full transition-all duration-200',
                status === 'running' && 'bg-blue-500 animate-pulse',
                status === 'complete' && 'bg-green-500',
                status === 'error' && 'bg-red-500',
                status === 'pending' && 'bg-muted'
              )}
              title={STEP_LABELS[stepKey]}
            />
          )
        })}
      </div>

      {/* Current step label */}
      {currentStep && (
        <span className="text-sm text-muted-foreground">
          {current?.message || (current?.data?.message as string | undefined) || STEP_LABELS[currentStep]}
        </span>
      )}
    </div>
  )
}
