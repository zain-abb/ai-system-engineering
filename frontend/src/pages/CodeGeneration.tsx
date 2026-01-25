import { useEffect } from 'react'
import { Loader2, Sparkles, XCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ResultDisplay } from '@/components/ResultDisplay'
import { ProcessingSteps } from '@/components/ProcessingSteps'
import { useToast } from '@/hooks/use-toast'
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration'
import { useCapabilityState } from '@/contexts/CapabilityStateContext'
import { useSettings } from '@/contexts/SettingsContext'
import type { CodeGenRequest, CodeGenResponse } from '@/types/api'

const languages = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
]

export default function CodeGeneration() {
  const { toast } = useToast()
  const { model } = useSettings()
  const { codeGeneration, setCodeGeneration, resetCodeGeneration } = useCapabilityState()

  const {
    isStreaming,
    steps,
    currentStep,
    result,
    error,
    startGeneration,
    cancel,
    reset: resetStreaming,
  } = useStreamingGeneration<CodeGenRequest, CodeGenResponse>('/code/generate/stream')

  // Sync streaming result to context when it changes
  useEffect(() => {
    if (result) {
      setCodeGeneration({ result, steps })
    }
  }, [result, steps, setCodeGeneration])

  // Use context state or streaming state
  const displayResult = result || codeGeneration.result
  const displaySteps = steps.size > 0 ? steps : codeGeneration.steps

  const handleGenerate = async () => {
    if (!codeGeneration.requirements.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Requirements',
        description: 'Please enter your code requirements.',
      })
      return
    }

    await startGeneration({
      requirements: codeGeneration.requirements,
      language: codeGeneration.language,
      context: codeGeneration.context || undefined,
      model,
    })
  }

  const handleCancel = () => {
    cancel()
    toast({
      title: 'Generation Cancelled',
      description: 'The code generation was stopped.',
    })
  }

  const handleReset = () => {
    resetStreaming()
    resetCodeGeneration()
  }

  // Show error toast when an error occurs
  useEffect(() => {
    if (error && !isStreaming) {
      toast({
        variant: 'destructive',
        title: 'Generation Failed',
        description: error,
      })
    }
  }, [error, isStreaming, toast])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Generate Code</h2>
        <p className="text-muted-foreground">
          Describe what you need and let AI generate the code for you
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Requirements</CardTitle>
              <CardDescription>
                Describe the code you want to generate in natural language
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="requirements">What do you want to build?</Label>
                <Textarea
                  id="requirements"
                  placeholder="e.g., Create a function that calculates the factorial of a number using recursion..."
                  value={codeGeneration.requirements}
                  onChange={(e) => setCodeGeneration({ requirements: e.target.value })}
                  className="min-h-[150px]"
                  disabled={isStreaming}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="language">Programming Language</Label>
                <Select
                  value={codeGeneration.language}
                  onValueChange={(value) => setCodeGeneration({ language: value })}
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
                <Label htmlFor="context">Context (Optional)</Label>
                <Textarea
                  id="context"
                  placeholder="Add any existing code or additional context..."
                  value={codeGeneration.context}
                  onChange={(e) => setCodeGeneration({ context: e.target.value })}
                  className="min-h-[100px]"
                  disabled={isStreaming}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={isStreaming ? handleCancel : handleGenerate}
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
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate Code
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
              <ResultDisplay
                title="Generated Code"
                content={displayResult.result}
                language={codeGeneration.language}
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
                    <p>Generating code...</p>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Generated code will appear here</p>
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
