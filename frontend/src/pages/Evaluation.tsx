import { useState } from 'react'
import { Shield, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { CodeEditor } from '@/components/CodeEditor'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

// Mock evaluation function (would call backend in real implementation)
async function evaluateCode(code: string, _prompt: string) {
  // Simulate API call
  await new Promise((resolve) => setTimeout(resolve, 1500))

  // Mock evaluation results
  return {
    overall_score: 0.78,
    overall_passed: true,
    results: {
      correctness: {
        score: 0.85,
        passed: true,
        issues: [
          { severity: 'low', category: 'style', description: 'Consider adding type hints' },
        ],
      },
      robustness: {
        score: 0.72,
        passed: true,
        issues: [
          { severity: 'medium', category: 'edge_case', description: 'Missing null check' },
        ],
      },
      safety: {
        score: 0.90,
        passed: true,
        issues: [],
      },
      hallucination: {
        score: 0.65,
        passed: false,
        issues: [
          { severity: 'high', category: 'invalid_import', description: 'Module "utils.helpers" may not exist' },
        ],
      },
    },
  }
}

const severityIcons = {
  critical: <XCircle className="h-4 w-4 text-red-600" />,
  high: <XCircle className="h-4 w-4 text-red-500" />,
  medium: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
  low: <Info className="h-4 w-4 text-blue-500" />,
  info: <Info className="h-4 w-4 text-gray-500" />,
}

interface EvalResult {
  score: number
  passed: boolean
  issues: Array<{ severity: string; category: string; description: string }>
}

function MetricCard({
  title,
  result,
}: {
  title: string
  result?: EvalResult
}) {
  if (!result) return null

  const scorePercent = result.score * 100

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {result.passed ? (
            <CheckCircle className="h-5 w-5 text-green-500" />
          ) : (
            <XCircle className="h-5 w-5 text-red-500" />
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-2xl font-bold">{scorePercent.toFixed(0)}%</span>
          <span
            className={cn(
              'text-xs font-medium px-2 py-1 rounded',
              result.passed
                ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
            )}
          >
            {result.passed ? 'PASSED' : 'FAILED'}
          </span>
        </div>
        <Progress value={scorePercent} className="h-2" />
        {result.issues.length > 0 && (
          <div className="space-y-2 pt-2 border-t">
            <p className="text-xs font-medium text-muted-foreground">
              Issues ({result.issues.length})
            </p>
            {result.issues.slice(0, 3).map((issue, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                {severityIcons[issue.severity as keyof typeof severityIcons] || severityIcons.info}
                <span>{issue.description}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function Evaluation() {
  const [code, setCode] = useState('')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Awaited<ReturnType<typeof evaluateCode>> | null>(null)
  const { toast } = useToast()

  const handleEvaluate = async () => {
    if (!code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter code to evaluate.',
      })
      return
    }

    setLoading(true)
    try {
      const evalResult = await evaluateCode(code, prompt)
      setResult(evalResult)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Evaluation Failed',
        description: (error as Error).message,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Code Evaluation</h2>
        <p className="text-muted-foreground">
          Evaluate code for correctness, robustness, safety, and hallucination
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Code to Evaluate</CardTitle>
              <CardDescription>
                Enter the generated code you want to evaluate
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Code</Label>
                <CodeEditor
                  value={code}
                  onChange={setCode}
                  language="python"
                  placeholder="Paste generated code here..."
                  minHeight="200px"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="prompt">Original Prompt (Optional)</Label>
                <Textarea
                  id="prompt"
                  placeholder="The prompt used to generate this code..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[80px]"
                />
              </div>

              <Button
                onClick={handleEvaluate}
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Shield className="mr-2 h-4 w-4 animate-pulse" />
                    Evaluating...
                  </>
                ) : (
                  <>
                    <Shield className="mr-2 h-4 w-4" />
                    Evaluate Code
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Results Section */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Overall Score */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Overall Score</CardTitle>
                    {result.overall_passed ? (
                      <CheckCircle className="h-6 w-6 text-green-500" />
                    ) : (
                      <XCircle className="h-6 w-6 text-red-500" />
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <span className="text-4xl font-bold">
                      {(result.overall_score * 100).toFixed(0)}%
                    </span>
                    <Progress
                      value={result.overall_score * 100}
                      className="flex-1 h-3"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Individual Metrics */}
              <div className="grid gap-4 sm:grid-cols-2">
                <MetricCard title="Correctness" result={result.results.correctness} />
                <MetricCard title="Robustness" result={result.results.robustness} />
                <MetricCard title="Safety" result={result.results.safety} />
                <MetricCard title="Hallucination" result={result.results.hallucination} />
              </div>
            </>
          ) : (
            <Card className="h-full min-h-[400px] flex items-center justify-center">
              <CardContent className="text-center text-muted-foreground">
                <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Evaluation results will appear here</p>
                <p className="text-sm mt-2">
                  Checks for correctness, robustness, safety, and hallucination
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
