import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface MarkdownRendererProps {
  content: string
  className?: string
  title?: string
  showCopy?: boolean
  maxHeight?: string
}

export function MarkdownRenderer({
  content,
  className,
  title,
  showCopy = true,
  maxHeight = '500px'
}: MarkdownRendererProps) {
  const [copied, setCopied] = useState(false)
  const isDark = document.documentElement.classList.contains('dark')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const markdownContent = (
    <div className={cn('markdown-body', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Code blocks with syntax highlighting
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const isInline = !match && !className

            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-muted font-mono text-sm"
                  {...props}
                >
                  {children}
                </code>
              )
            }

            return (
              <SyntaxHighlighter
                style={isDark ? oneDark : oneLight}
                language={match?.[1] || 'text'}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                }}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            )
          },
          // Headings
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold mt-6 mb-4 pb-2 border-b border-border first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold mt-5 mb-3 pb-2 border-b border-border">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold mt-4 mb-2">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-semibold mt-3 mb-2">{children}</h4>
          ),
          // Paragraphs
          p: ({ children }) => (
            <p className="my-3 leading-relaxed first:mt-0">{children}</p>
          ),
          // Lists
          ul: ({ children }) => (
            <ul className="my-3 ml-6 list-disc space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 ml-6 list-decimal space-y-1">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed">{children}</li>
          ),
          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="my-3 pl-4 border-l-4 border-muted-foreground/30 text-muted-foreground italic">
              {children}
            </blockquote>
          ),
          // Tables
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table className="min-w-full border-collapse border border-border rounded-lg">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/50">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2 text-left font-semibold border border-border">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 border border-border">{children}</td>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-muted/30">{children}</tr>
          ),
          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-primary hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          // Horizontal rule
          hr: () => <hr className="my-6 border-border" />,
          // Strong/Bold
          strong: ({ children }) => (
            <strong className="font-semibold">{children}</strong>
          ),
          // Emphasis/Italic
          em: ({ children }) => <em className="italic">{children}</em>,
          // Pre blocks (fallback for code without language)
          pre: ({ children }) => (
            <pre className="my-3 p-4 bg-muted rounded-lg overflow-x-auto">
              {children}
            </pre>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )

  // If title is provided, wrap in a Card
  if (title) {
    return (
      <Card className="overflow-hidden">
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
        <CardContent className="p-4 pt-0" style={{ maxHeight, overflow: 'auto' }}>
          {markdownContent}
        </CardContent>
      </Card>
    )
  }

  // Without title, just return the markdown content
  return markdownContent
}
