import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, Search } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { CodeEditor } from '@/components/CodeEditor'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'

const languages = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
]

const focusAreas = [
  { value: '', label: 'General Review' },
  { value: 'security', label: 'Security' },
  { value: 'performance', label: 'Performance' },
  { value: 'readability', label: 'Readability' },
  { value: 'best-practices', label: 'Best Practices' },
  { value: 'bugs', label: 'Bug Detection' },
]

export default function CodeReview() {
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [focus, setFocus] = useState('')
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: api.reviewCode,
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Review Failed',
        description: error.message,
      })
    },
  })

  const handleReview = () => {
    if (!code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter code to review.',
      })
      return
    }

    mutation.mutate({
      code,
      language,
      focus: focus || undefined,
    })
  }

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
                  <Select value={language} onValueChange={setLanguage}>
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
                  <Select value={focus} onValueChange={setFocus}>
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
                  value={code}
                  onChange={setCode}
                  language={language}
                  placeholder="Paste your code here for review..."
                  minHeight="300px"
                />
              </div>

              <Button
                onClick={handleReview}
                disabled={mutation.isPending}
                className="w-full"
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Reviewing...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Review Code
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
                  <CardTitle>Review Results</CardTitle>
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
                <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Review results will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
