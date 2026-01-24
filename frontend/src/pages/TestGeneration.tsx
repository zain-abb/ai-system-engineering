import { useEffect } from 'react'
import { Loader2, TestTube2, XCircle } from 'lucide-react'
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
import { ResultDisplay } from '@/components/ResultDisplay'
import { ProcessingSteps } from '@/components/ProcessingSteps'
import { useToast } from '@/hooks/use-toast'
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration'
import { useCapabilityState } from '@/contexts/CapabilityStateContext'
import type { TestGenRequest, TestGenResponse } from '@/types/api'

const languages = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
]

const frameworks = {
  python: [
    { value: 'pytest', label: 'pytest' },
    { value: 'unittest', label: 'unittest' },
  ],
  javascript: [
    { value: 'jest', label: 'Jest' },
    { value: 'mocha', label: 'Mocha' },
  ],
  typescript: [
    { value: 'jest', label: 'Jest' },
    { value: 'vitest', label: 'Vitest' },
  ],
  java: [
    { value: 'junit', label: 'JUnit' },
    { value: 'testng', label: 'TestNG' },
  ],
}

export default function TestGeneration() {
  const { toast } = useToast()
  const { testGeneration, setTestGeneration, resetTestGeneration } = useCapabilityState()

  const {
    isStreaming,
    steps,
    currentStep,
    result,
    error,
    startGeneration,
    cancel,
    reset: resetStreaming,
  } = useStreamingGeneration<TestGenRequest, TestGenResponse>('/tests/generate/stream')

  // Sync streaming result to context when it changes
  useEffect(() => {
    if (result) {
      setTestGeneration({ result, steps })
    }
  }, [result, steps, setTestGeneration])

  // Use context state or streaming state
  const displayResult = result || testGeneration.result
  const displaySteps = steps.size > 0 ? steps : testGeneration.steps

  const handleLanguageChange = (value: string) => {
    setTestGeneration({ language: value })
    const availableFrameworks = frameworks[value as keyof typeof frameworks]
    if (availableFrameworks.length > 0) {
      setTestGeneration({ framework: availableFrameworks[0].value })
    }
  }

  const handleGenerate = async () => {
    if (!testGeneration.code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter the code you want to test.',
      })
      return
    }

    await startGeneration({
      code: testGeneration.code,
      language: testGeneration.language,
      framework: testGeneration.framework,
    })
  }

  const handleCancel = () => {
    cancel()
    toast({
      title: 'Generation Cancelled',
      description: 'The test generation was stopped.',
    })
  }

  const handleReset = () => {
    resetStreaming()
    resetTestGeneration()
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

  const availableFrameworks = frameworks[testGeneration.language as keyof typeof frameworks] || []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Generate Tests</h2>
        <p className="text-muted-foreground">
          Automatically create unit tests for your code
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Source Code</CardTitle>
              <CardDescription>
                Paste the code you want to generate tests for
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="language">Language</Label>
                  <Select
                    value={testGeneration.language}
                    onValueChange={handleLanguageChange}
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
                  <Label htmlFor="framework">Test Framework</Label>
                  <Select
                    value={testGeneration.framework}
                    onValueChange={(value) => setTestGeneration({ framework: value })}
                    disabled={isStreaming}
                  >
                    <SelectTrigger id="framework">
                      <SelectValue placeholder="Select framework" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableFrameworks.map((fw) => (
                        <SelectItem key={fw.value} value={fw.value}>
                          {fw.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Code to Test</Label>
                <CodeEditor
                  value={testGeneration.code}
                  onChange={(value) => setTestGeneration({ code: value })}
                  language={testGeneration.language}
                  placeholder="Paste your code here..."
                  minHeight="250px"
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
                      <TestTube2 className="mr-2 h-4 w-4" />
                      Generate Tests
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
                title="Generated Tests"
                content={displayResult.result}
                language={testGeneration.language}
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
                    <p>Generating tests...</p>
                  </>
                ) : (
                  <>
                    <TestTube2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Generated tests will appear here</p>
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
