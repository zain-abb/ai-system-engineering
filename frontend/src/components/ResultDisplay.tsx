import { Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ResultDisplayProps {
  title?: string
  content: string
  language?: string
  isCode?: boolean
  className?: string
  showCopy?: boolean
}

export function ResultDisplay({
  title,
  content,
  language = 'python',
  isCode = true,
  className,
  showCopy = true,
}: ResultDisplayProps) {
  const [copied, setCopied] = useState(false)
  const isDark = document.documentElement.classList.contains('dark')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Detect if content looks like code
  const detectIsCode = () => {
    const codeIndicators = ['def ', 'class ', 'import ', 'function ', 'const ', 'let ', 'var ', '```']
    return codeIndicators.some((indicator) => content.includes(indicator))
  }

  const shouldShowAsCode = isCode || detectIsCode()

  return (
    <Card className={cn('overflow-hidden', className)}>
      {title && (
        <CardHeader className="flex flex-row items-center justify-between py-3">
          <CardTitle className="text-lg">{title}</CardTitle>
          {showCopy && content && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 px-2"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-1" />
                  Copy
                </>
              )}
            </Button>
          )}
        </CardHeader>
      )}
      <CardContent className={cn(!title && 'pt-6', 'p-0')}>
        {shouldShowAsCode ? (
          <SyntaxHighlighter
            language={language}
            style={isDark ? oneDark : oneLight}
            customStyle={{
              margin: 0,
              fontSize: '14px',
              borderRadius: title ? '0' : '0.375rem',
              maxHeight: '500px',
            }}
            showLineNumbers
          >
            {content || '// No content'}
          </SyntaxHighlighter>
        ) : (
          <div className="p-4 prose dark:prose-invert max-w-none">
            <pre className="whitespace-pre-wrap text-sm">{content}</pre>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
