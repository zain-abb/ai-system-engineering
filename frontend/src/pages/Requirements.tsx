import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, FileText } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'

export default function Requirements() {
  const [requirements, setRequirements] = useState('')
  const [context, setContext] = useState('')
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: (data: { prompt: string; context?: string }) =>
      api.generate({
        prompt: data.prompt,
        task_type: 'requirements',
        context: data.context,
      }),
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Analysis Failed',
        description: error.message,
      })
    },
  })

  const handleAnalyze = () => {
    if (!requirements.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Requirements',
        description: 'Please enter requirements to analyze.',
      })
      return
    }

    mutation.mutate({
      prompt: requirements,
      context: context || undefined,
    })
  }

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
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  className="min-h-[250px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="context">Project Context (Optional)</Label>
                <Textarea
                  id="context"
                  placeholder="Add project context, constraints, or existing architecture details..."
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  className="min-h-[100px]"
                />
              </div>

              <Button
                onClick={handleAnalyze}
                disabled={mutation.isPending}
                className="w-full"
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    Analyze Requirements
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Output Section */}
        <div className="space-y-4">
          {mutation.data ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Analysis Results</CardTitle>
                  <CardDescription>
                    Confidence: {(mutation.data.confidence * 100).toFixed(0)}%
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="prose dark:prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg overflow-auto max-h-[500px]">
                      {mutation.data.result}
                    </pre>
                  </div>
                </CardContent>
              </Card>
              {mutation.data.usage && (
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>Tokens: {mutation.data.usage.total_tokens || 'N/A'}</span>
                      <span>Cost: ${mutation.data.usage.cost?.toFixed(4) || '0.0000'}</span>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="h-full min-h-[400px] flex items-center justify-center">
              <CardContent className="text-center text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Analysis results will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
