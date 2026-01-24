import { useState } from 'react'
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'
import type { HistoryItem } from '@/types/api'

export interface ConversationTurn {
  user: HistoryItem
  assistant: HistoryItem | null
}

interface ConversationModalProps {
  turn: ConversationTurn | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function formatCapability(capability: string | undefined): string {
  if (!capability) return 'Unknown'
  return capability
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function ConversationModal({ turn, open, onOpenChange }: ConversationModalProps) {
  const [userExpanded, setUserExpanded] = useState(false)
  const [copiedUser, setCopiedUser] = useState(false)
  const [copiedAssistant, setCopiedAssistant] = useState(false)
  const { toast } = useToast()

  if (!turn) return null

  const capability = turn.assistant?.metadata?.capability as string | undefined
  const userLineCount = turn.user.content.split('\n').length

  const copyToClipboard = async (text: string, type: 'user' | 'assistant') => {
    await navigator.clipboard.writeText(text)
    if (type === 'user') {
      setCopiedUser(true)
      setTimeout(() => setCopiedUser(false), 2000)
    } else {
      setCopiedAssistant(true)
      setTimeout(() => setCopiedAssistant(false), 2000)
    }
    toast({ title: 'Copied to clipboard' })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!flex !flex-col max-w-6xl w-[90vw] h-[90vh] p-0">
        <DialogHeader className="flex-shrink-0 p-6 pb-4">
          <DialogTitle className="flex items-center gap-2">
            Conversation
            {capability && (
              <Badge variant="secondary">{formatCapability(capability)}</Badge>
            )}
          </DialogTitle>
          <DialogDescription>
            {new Date(turn.user.timestamp).toLocaleString()}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-y-auto px-6 pb-6 space-y-6">
          {/* User Message - Collapsible */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Badge>User</Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(turn.user.content, 'user')}
                className="h-8 px-2"
              >
                {copiedUser ? (
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
            </div>
            <div
              className="bg-muted/50 rounded-lg p-4 cursor-pointer transition-colors hover:bg-muted/70"
              onClick={() => setUserExpanded(!userExpanded)}
            >
              <pre
                className={cn(
                  'whitespace-pre-wrap font-mono text-sm',
                  !userExpanded && 'line-clamp-3'
                )}
              >
                {turn.user.content}
              </pre>
              {userLineCount > 3 && (
                <span className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  {userExpanded ? (
                    <>
                      <ChevronUp className="h-3 w-3" /> Click to collapse
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-3 w-3" /> Click to expand
                    </>
                  )}
                </span>
              )}
            </div>
          </div>

          {/* Assistant Response */}
          {turn.assistant && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <Badge variant="secondary">Assistant</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(turn.assistant!.content, 'assistant')}
                  className="h-8 px-2"
                >
                  {copiedAssistant ? (
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
              </div>
              <div className="bg-muted/30 rounded-lg p-4">
                <MarkdownRenderer
                  content={turn.assistant.content}
                  showCopy={false}
                  maxHeight="none"
                />
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
