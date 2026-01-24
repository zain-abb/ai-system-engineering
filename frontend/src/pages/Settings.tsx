import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, FolderOpen, Trash2, Database, History, Cpu } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'
import { useSettings, CLAUDE_MODELS } from '@/contexts/SettingsContext'
import { ConversationModal, type ConversationTurn } from '@/components/ConversationModal'

// localStorage keys
const STORAGE_KEYS = {
  INDEX_DIRECTORY: 'se-agent-index-directory',
  EXTENSIONS: 'se-agent-extensions',
}

export default function Settings() {
  const { model, setModel } = useSettings()
  const [indexDirectory, setIndexDirectory] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.INDEX_DIRECTORY) || ''
  })
  const [extensions, setExtensions] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.EXTENSIONS) || '.py, .js, .ts'
  })

  // Persist to localStorage when values change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.INDEX_DIRECTORY, indexDirectory)
  }, [indexDirectory])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.EXTENSIONS, extensions)
  }, [extensions])
  const [selectedTurn, setSelectedTurn] = useState<ConversationTurn | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: api.getUsage,
  })

  const { data: ragStats } = useQuery({
    queryKey: ['ragStats'],
    queryFn: api.getRagStats,
  })

  const { data: history } = useQuery({
    queryKey: ['history'],
    queryFn: api.getHistory,
  })

  // Group messages into conversation turns (user + assistant pairs)
  const conversationTurns = useMemo(() => {
    if (!history) return []
    const turns: ConversationTurn[] = []
    for (let i = 0; i < history.length; i++) {
      if (history[i].role === 'user') {
        turns.push({
          user: history[i],
          assistant: history[i + 1]?.role === 'assistant' ? history[i + 1] : null,
        })
      }
    }
    return turns
  }, [history])

  // Format capability name for display
  const formatCapability = (capability: unknown): string => {
    if (typeof capability !== 'string' || !capability) return 'Unknown'
    return capability
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const indexMutation = useMutation({
    mutationFn: api.indexCodebase,
    onSuccess: (data) => {
      toast({
        title: 'Indexing Complete',
        description: `Indexed ${data.chunks_indexed} chunks from ${data.directory}`,
      })
      queryClient.invalidateQueries({ queryKey: ['ragStats'] })
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Indexing Failed',
        description: error.message,
      })
    },
  })

  const clearHistoryMutation = useMutation({
    mutationFn: api.clearHistory,
    onSuccess: () => {
      toast({
        title: 'History Cleared',
        description: 'Conversation history has been cleared.',
      })
      queryClient.invalidateQueries({ queryKey: ['history'] })
    },
    onError: (error: Error) => {
      toast({
        variant: 'destructive',
        title: 'Failed to Clear History',
        description: error.message,
      })
    },
  })

  const handleIndex = () => {
    if (!indexDirectory.trim()) {
      toast({
        variant: 'destructive',
        title: 'Missing Directory',
        description: 'Please enter a directory path to index.',
      })
      return
    }

    const extList = extensions
      .split(',')
      .map((e) => e.trim())
      .filter((e) => e)

    indexMutation.mutate({
      directory: indexDirectory,
      extensions: extList.length > 0 ? extList : undefined,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">
          Configure the SE-Agent and manage resources
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* AI Model Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              AI Model
            </CardTitle>
            <CardDescription>
              Select the Claude model for all generations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {CLAUDE_MODELS.map((m) => (
                <div
                  key={m.id}
                  onClick={() => setModel(m.id)}
                  className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                    model === m.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <div>
                    <p className="font-medium">{m.name}</p>
                    <p className="text-sm text-muted-foreground">{m.description}</p>
                  </div>
                  {model === m.id && <div className="h-2 w-2 rounded-full bg-primary" />}
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Selected: <code className="bg-muted px-1 rounded">{model}</code>
            </p>
          </CardContent>
        </Card>

        {/* RAG Indexing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              RAG Index
            </CardTitle>
            <CardDescription>
              Index your codebase for context-aware generation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="directory">Directory Path</Label>
              <Textarea
                id="directory"
                placeholder="/path/to/your/codebase"
                value={indexDirectory}
                onChange={(e) => setIndexDirectory(e.target.value)}
                className="min-h-[60px]"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="extensions">File Extensions (comma-separated)</Label>
              <Textarea
                id="extensions"
                placeholder=".py, .js, .ts"
                value={extensions}
                onChange={(e) => setExtensions(e.target.value)}
                className="min-h-[40px]"
              />
            </div>

            <Button
              onClick={handleIndex}
              disabled={indexMutation.isPending}
              className="w-full"
            >
              {indexMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Indexing...
                </>
              ) : (
                <>
                  <FolderOpen className="mr-2 h-4 w-4" />
                  Index Codebase
                </>
              )}
            </Button>

            <Separator />

            {/* RAG Stats */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Index Status</p>
              {ragStats?.total_chunks !== undefined ? (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Indexed Chunks</span>
                    <span className="font-medium">{ragStats.total_chunks}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Indexed Files</span>
                    <span className="font-medium">{ragStats.indexed_files || 0}</span>
                  </div>
                  <Progress value={ragStats.total_chunks ? 100 : 0} className="h-2" />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No codebase indexed yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Usage Stats */}
        <Card>
          <CardHeader>
            <CardTitle>API Usage</CardTitle>
            <CardDescription>
              Your API usage statistics
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Total Requests</p>
                <p className="text-2xl font-bold">
                  {usage?.total_requests?.toLocaleString() || 0}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Total Cost</p>
                <p className="text-2xl font-bold">
                  ${usage?.total_cost?.toFixed(4) || '0.0000'}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Input Tokens</p>
                <p className="text-lg font-semibold">
                  {usage?.input_tokens?.toLocaleString() || 0}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Output Tokens</p>
                <p className="text-lg font-semibold">
                  {usage?.output_tokens?.toLocaleString() || 0}
                </p>
              </div>
            </div>

            <Separator />

            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Total Tokens</p>
              <p className="text-lg font-semibold">
                {usage?.total_tokens?.toLocaleString() || 0}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Conversation History */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Conversation History
                </CardTitle>
                <CardDescription>
                  {conversationTurns.length} conversation{conversationTurns.length !== 1 ? 's' : ''} in history
                </CardDescription>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => clearHistoryMutation.mutate()}
                disabled={clearHistoryMutation.isPending || !history?.length}
              >
                {clearHistoryMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Trash2 className="mr-2 h-4 w-4" />
                    Clear History
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {conversationTurns.length > 0 ? (
              <div className="space-y-2 max-h-[400px] overflow-auto">
                {conversationTurns.map((turn, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      setSelectedTurn(turn)
                      setModalOpen(true)
                    }}
                    className="p-3 rounded-lg bg-muted/50 cursor-pointer hover:bg-muted/70 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs">
                        {formatCapability(turn.assistant?.metadata?.capability)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {new Date(turn.user.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm truncate">{turn.user.content}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No conversation history yet
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <ConversationModal
        turn={selectedTurn}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </div>
  )
}
