import { useEffect } from 'react'
import { Loader2, Search, XCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { CodeEditor } from '@/components/CodeEditor'
import { ProcessingSteps } from '@/components/ProcessingSteps'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { useToast } from '@/hooks/use-toast'
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration'
import { useCapabilityState } from '@/contexts/CapabilityStateContext'
import { useSettings } from '@/contexts/SettingsContext'
import type { CodeReviewRequest, ReviewResponse } from '@/types/api'

const languages = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
]

const focusAreas = [
  { value: 'general', label: 'General Review' },
  { value: 'security', label: 'Security' },
  { value: 'performance', label: 'Performance' },
  { value: 'readability', label: 'Readability' },
  { value: 'best-practices', label: 'Best Practices' },
  { value: 'bugs', label: 'Bug Detection' },
]

export default function CodeReview() {
  const { toast } = useToast()
  const { model } = useSettings()
  const { codeReview, setCodeReview, resetCodeReview } = useCapabilityState()

  const {
    isStreaming,
    steps,
    currentStep,
    result,
    error,
    startGeneration,
    cancel,
    reset: resetStreaming,
  } = useStreamingGeneration<CodeReviewRequest, ReviewResponse>('/code/review/stream')

  // Sync streaming result to context when it changes
  useEffect(() => {
    if (result) {
      setCodeReview({ result, steps })
    }
  }, [result, steps, setCodeReview])

  // Use context state or streaming state
  const displayResult = result || codeReview.result
  const displaySteps = steps.size > 0 ? steps : codeReview.steps

  const handleReview = async () => {
    if (!codeReview.code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter code to review.',
      })
      return
    }

    await startGeneration({
      code: codeReview.code,
      language: codeReview.language,
      focus: codeReview.focus === 'general' ? undefined : codeReview.focus,
      model,
    })
  }

  const handleCancel = () => {
    cancel()
    toast({
      title: 'Review Cancelled',
      description: 'The code review was stopped.',
    })
  }

  const handleReset = () => {
    resetStreaming()
    resetCodeReview()
  }

  // Show error toast when an error occurs
  useEffect(() => {
    if (error && !isStreaming) {
      toast({
        variant: 'destructive',
        title: 'Review Failed',
        description: error,
      })
    }
  }, [error, isStreaming, toast])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Code Review</h2>
        <p className="text-muted-foreground">
          Get detailed feedback on code quality, bugs, and improvements
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Code to Review</CardTitle>
              <CardDescription>
                Paste your code for AI-powered review
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="language">Language</Label>
                  <Select
                    value={codeReview.language}
                    onValueChange={(value) => setCodeReview({ language: value })}
                    disabled={isStreaming}
                  >
                    <SelectTrigger id="language">
                      <SelectValue placeholder="Select language" />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((lang) => (
                        <SelectItem key={lang.value} value={lang.value}>
                          {lang.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="focus">Focus Area</Label>
                  <Select
                    value={codeReview.focus}
                    onValueChange={(value) => setCodeReview({ focus: value })}
                    disabled={isStreaming}
                  >
                    <SelectTrigger id="focus">
                      <SelectValue placeholder="Select focus" />
                    </SelectTrigger>
                    <SelectContent>
                      {focusAreas.map((area) => (
                        <SelectItem key={area.value} value={area.value}>
                          {area.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Code</Label>
                <CodeEditor
                  value={codeReview.code}
                  onChange={(value) => setCodeReview({ code: value })}
                  language={codeReview.language}
                  placeholder="Paste your code here for review..."
                  minHeight="300px"
                  disabled={isStreaming}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={isStreaming ? handleCancel : handleReview}
                  variant={isStreaming ? 'destructive' : 'default'}
                  className="flex-1"
                >
                  {isStreaming ? (
                    <>
                      <XCircle className="mr-2 h-4 w-4" />
                      Cancel
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Review Code
                    </>
                  )}
                </Button>
                {displayResult && !isStreaming && (
                  <Button variant="outline" onClick={handleReset}>
                    Clear
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Processing Steps - shown during streaming */}
          {(isStreaming || displaySteps.size > 0) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  {isStreaming && <Loader2 className="h-4 w-4 animate-spin" />}
                  Processing
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ProcessingSteps steps={displaySteps} currentStep={currentStep} />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Output Section */}
        <div className="space-y-4">
          {displayResult ? (
            <>
              <MarkdownRenderer
                content={displayResult.result}
                title="Review Results"
              />
              {displayResult.usage && (
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>
                        Tokens: {
                          ((displayResult.usage.input_tokens as number | undefined) ?? 0) +
                          ((displayResult.usage.output_tokens as number | undefined) ?? 0) ||
                          (displayResult.usage.total_tokens as number | undefined) ||
                          'N/A'
                        }
                      </span>
                      <span>Cost: ${((displayResult.usage.cost as number | undefined) ?? 0).toFixed(4)}</span>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="h-full min-h-[400px] flex items-center justify-center">
              <CardContent className="text-center text-muted-foreground">
                {isStreaming ? (
                  <>
                    <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin opacity-50" />
                    <p>Reviewing code...</p>
                  </>
                ) : (
                  <>
                    <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Review results will appear here</p>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
