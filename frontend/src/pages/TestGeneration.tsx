import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, TestTube2 } from 'lucide-react'
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
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'

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
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [framework, setFramework] = useState('pytest')
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: api.generateTests,
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Generation Failed',
        description: error.message,
      })
    },
  })

  const handleLanguageChange = (value: string) => {
    setLanguage(value)
    const availableFrameworks = frameworks[value as keyof typeof frameworks]
    if (availableFrameworks.length > 0) {
      setFramework(availableFrameworks[0].value)
    }
  }

  const handleGenerate = () => {
    if (!code.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Code',
        description: 'Please enter the code you want to test.',
      })
      return
    }

    mutation.mutate({
      code,
      language,
      framework,
    })
  }

  const availableFrameworks = frameworks[language as keyof typeof frameworks] || []

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
                  <Select value={language} onValueChange={handleLanguageChange}>
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
                  <Select value={framework} onValueChange={setFramework}>
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
                  value={code}
                  onChange={setCode}
                  language={language}
                  placeholder="Paste your code here..."
                  minHeight="250px"
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
                    Generating Tests...
                  </>
                ) : (
                  <>
                    <TestTube2 className="mr-2 h-4 w-4" />
                    Generate Tests
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
                title="Generated Tests"
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
                <TestTube2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Generated tests will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
