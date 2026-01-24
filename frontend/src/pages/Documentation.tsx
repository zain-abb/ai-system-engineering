import { useEffect } from 'react'
import { Loader2, BookOpen, XCircle } from 'lucide-react'
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
import type { GenerateRequest, GenerateResponse } from '@/types/api'

const languages = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
]

const docTypes = [
  { value: 'API', label: 'API Documentation' },
  { value: 'README', label: 'README' },
  { value: 'inline', label: 'Inline Comments' },
  { value: 'comprehensive', label: 'Comprehensive Docs' },
]

export default function Documentation() {
  const { toast } = useToast()
  const { model } = useSettings()
  const { documentation, setDocumentation, resetDocumentation } = useCapabilityState()

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
      setDocumentation({ result, steps })
    }
  }, [result, steps, setDocumentation])

  // Use context state or streaming state
  const displayResult = result || documentation.result
  const displaySteps = steps.size > 0 ? steps : documentation.steps

  const handleGenerate = async () => {
    if (!documentation.code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter code to document.',
      })
      return
    }

    await startGeneration({
      prompt: `Generate ${documentation.docType} documentation for this code:\n\n${documentation.code}`,
      task_type: 'documentation',
      language: documentation.language,
      model,
    })
  }

  const handleCancel = () => {
    cancel()
    toast({
      title: 'Generation Cancelled',
      description: 'The documentation generation was stopped.',
    })
  }

  const handleReset = () => {
    resetStreaming()
    resetDocumentation()
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
        <h2 className="text-3xl font-bold tracking-tight">Documentation</h2>
        <p className="text-muted-foreground">
          Generate documentation for your code
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Code to Document</CardTitle>
              <CardDescription>
                Paste your code to generate documentation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="language">Language</Label>
                  <Select
                    value={documentation.language}
                    onValueChange={(value) => setDocumentation({ language: value })}
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
                  <Label htmlFor="docType">Documentation Type</Label>
                  <Select
                    value={documentation.docType}
                    onValueChange={(value) => setDocumentation({ docType: value })}
                    disabled={isStreaming}
                  >
                    <SelectTrigger id="docType">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {docTypes.map((dt) => (
                        <SelectItem key={dt.value} value={dt.value}>
                          {dt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Code</Label>
                <CodeEditor
                  value={documentation.code}
                  onChange={(value) => setDocumentation({ code: value })}
                  language={documentation.language}
                  placeholder="Paste your code here..."
                  minHeight="300px"
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
                      <BookOpen className="mr-2 h-4 w-4" />
                      Generate Documentation
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
                title="Generated Documentation"
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
                    <p>Generating documentation...</p>
                  </>
                ) : (
                  <>
                    <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Generated documentation will appear here</p>
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
