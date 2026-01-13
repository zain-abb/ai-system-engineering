import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, Sparkles } from 'lucide-react'
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

export default function CodeGeneration() {
  const [requirements, setRequirements] = useState('')
  const [language, setLanguage] = useState('python')
  const [context, setContext] = useState('')
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: api.generateCode,
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Generation Failed',
        description: error.message,
      })
    },
  })

  const handleGenerate = () => {
    if (!requirements.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Requirements',
        description: 'Please enter your code requirements.',
      })
      return
    }

    mutation.mutate({
      requirements,
      language,
      context: context || undefined,
    })
  }

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
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  className="min-h-[150px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="language">Programming Language</Label>
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
                <Label htmlFor="context">Context (Optional)</Label>
                <Textarea
                  id="context"
                  placeholder="Add any existing code or additional context..."
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  className="min-h-[100px]"
                />
              </div>

              <Button
                onClick={handleGenerate}
                disabled={mutation.isPending}
                className="w-full"
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate Code
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
              <ResultDisplay
                title="Generated Code"
                content={mutation.data.result}
                language={language}
              />
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
                <Sparkles className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Generated code will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
