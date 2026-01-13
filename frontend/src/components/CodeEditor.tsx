import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface CodeEditorProps {
  value: string
  onChange?: (value: string) => void
  language?: string
  readOnly?: boolean
  placeholder?: string
  className?: string
  minHeight?: string
}

export function CodeEditor({
  value,
  onChange,
  language = 'python',
  readOnly = false,
  placeholder = 'Enter your code here...',
  className,
  minHeight = '300px',
}: CodeEditorProps) {
  const isDark = document.documentElement.classList.contains('dark')

  if (readOnly) {
    return (
      <div className={cn('rounded-md border overflow-hidden', className)}>
        <SyntaxHighlighter
          language={language}
          style={isDark ? oneDark : oneLight}
          customStyle={{
            margin: 0,
            minHeight,
            fontSize: '14px',
            borderRadius: '0.375rem',
          }}
          showLineNumbers
        >
          {value || '// No code to display'}
        </SyntaxHighlighter>
      </div>
    )
  }

  return (
    <Textarea
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder}
      className={cn(
        'font-mono text-sm resize-none',
        className
      )}
      style={{ minHeight }}
    />
  )
}
