import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, BookOpen } from 'lucide-react'
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
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'

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
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [docType, setDocType] = useState('API')
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: (data: { prompt: string; language: string }) =>
      api.generate({
        prompt: data.prompt,
        task_type: 'documentation',
        language: data.language,
      }),
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Generation Failed',
        description: error.message,
      })
    },
  })

  const handleGenerate = () => {
    if (!code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter code to document.',
      })
      return
    }

    mutation.mutate({
      prompt: `Generate ${docType} documentation for this code:\n\n${code}`,
      language,
    })
  }

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
                  <Label htmlFor="docType">Documentation Type</Label>
                  <Select value={docType} onValueChange={setDocType}>
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
                  value={code}
                  onChange={setCode}
                  language={language}
                  placeholder="Paste your code here..."
                  minHeight="300px"
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
                    <BookOpen className="mr-2 h-4 w-4" />
                    Generate Documentation
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
                  <CardTitle>Generated Documentation</CardTitle>
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
                <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Generated documentation will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
