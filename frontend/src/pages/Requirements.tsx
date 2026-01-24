import { useEffect } from 'react'
import { Loader2, FileText, XCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { ProcessingSteps } from '@/components/ProcessingSteps'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { useToast } from '@/hooks/use-toast'
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration'
import { useCapabilityState } from '@/contexts/CapabilityStateContext'
import { useSettings } from '@/contexts/SettingsContext'
import type { GenerateRequest, GenerateResponse } from '@/types/api'

export default function Requirements() {
  const { toast } = useToast()
  const { model } = useSettings()
  const { requirements, setRequirements, resetRequirements } = useCapabilityState()

  const {
    isStreaming,
    steps,
    currentStep,
    result,
    error,
    startGeneration,
    cancel,
    reset: resetStreaming,
  } = useStreamingGeneration<GenerateRequest, GenerateResponse>('/generate/stream')

  // Sync streaming result to context when it changes
  useEffect(() => {
    if (result) {
      setRequirements({ result, steps })
    }
  }, [result, steps, setRequirements])

  // Use context state or streaming state
  const displayResult = result || requirements.result
  const displaySteps = steps.size > 0 ? steps : requirements.steps

  const handleAnalyze = async () => {
    if (!requirements.requirements.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Requirements',
        description: 'Please enter requirements to analyze.',
      })
      return
    }

    await startGeneration({
      prompt: requirements.requirements,
      task_type: 'requirements',
      context: requirements.context || undefined,
      model,
    })
  }

  const handleCancel = () => {
    cancel()
    toast({
      title: 'Analysis Cancelled',
      description: 'The requirements analysis was stopped.',
    })
  }

  const handleReset = () => {
    resetStreaming()
    resetRequirements()
  }

  // Show error toast when an error occurs
  useEffect(() => {
    if (error && !isStreaming) {
      toast({
        variant: 'destructive',
        title: 'Analysis Failed',
        description: error,
      })
    }
  }, [error, isStreaming, toast])

  // Get confidence from raw result
  const confidence = displayResult
    ? ((displayResult.raw as unknown as Record<string, unknown>)?.confidence as number ?? 0)
    : 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Requirements Analysis</h2>
        <p className="text-muted-foreground">
          Analyze and structure software requirements
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Requirements</CardTitle>
              <CardDescription>
                Enter your software requirements for analysis
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="requirements">Requirements Text</Label>
                <Textarea
                  id="requirements"
                  placeholder="Enter your software requirements here...

Example:
- The system should allow users to register and login
- Users should be able to create, read, update, and delete posts
- The system should support file uploads up to 10MB
- All data should be encrypted at rest"
                  value={requirements.requirements}
                  onChange={(e) => setRequirements({ requirements: e.target.value })}
                  className="min-h-[250px]"
                  disabled={isStreaming}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="context">Project Context (Optional)</Label>
                <Textarea
                  id="context"
                  placeholder="Add project context, constraints, or existing architecture details..."
                  value={requirements.context}
                  onChange={(e) => setRequirements({ context: e.target.value })}
                  className="min-h-[100px]"
                  disabled={isStreaming}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={isStreaming ? handleCancel : handleAnalyze}
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
                      <FileText className="mr-2 h-4 w-4" />
                      Analyze Requirements
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
              <Card className="overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between py-3">
                  <div>
                    <CardTitle className="text-lg">Analysis Results</CardTitle>
                    <CardDescription>
                      Confidence: {(confidence * 100).toFixed(0)}%
                    </CardDescription>
                  </div>
                </CardHeader>
              </Card>
              <MarkdownRenderer
                content={displayResult.result}
                title="Analysis Details"
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
                    <p>Analyzing requirements...</p>
                  </>
                ) : (
                  <>
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Analysis results will appear here</p>
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
