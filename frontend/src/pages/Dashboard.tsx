import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Code2,
  TestTube2,
  Search,
  FileText,
  BookOpen,
  Shield,
  Activity,
  Zap,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { api } from '@/lib/api'

const quickActions = [
  {
    to: '/generate',
    icon: Code2,
    title: 'Generate Code',
    description: 'Create code from natural language',
    color: 'text-blue-500',
  },
  {
    to: '/tests',
    icon: TestTube2,
    title: 'Generate Tests',
    description: 'Create unit tests for your code',
    color: 'text-green-500',
  },
  {
    to: '/review',
    icon: Search,
    title: 'Review Code',
    description: 'Get feedback on code quality',
    color: 'text-purple-500',
  },
  {
    to: '/requirements',
    icon: FileText,
    title: 'Requirements',
    description: 'Analyze software requirements',
    color: 'text-orange-500',
  },
  {
    to: '/docs',
    icon: BookOpen,
    title: 'Documentation',
    description: 'Generate API documentation',
    color: 'text-pink-500',
  },
  {
    to: '/evaluate',
    icon: Shield,
    title: 'Evaluate',
    description: 'Check code quality metrics',
    color: 'text-red-500',
  },
]

export default function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
  })

  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: api.getUsage,
  })

  const { data: ragStats } = useQuery({
    queryKey: ['ragStats'],
    queryFn: api.getRagStats,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          AI-powered software engineering assistant
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Activity className={`h-4 w-4 ${health?.agent_ready ? 'text-green-500' : 'text-yellow-500'}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">
              {health?.status || 'Loading...'}
            </div>
            <p className="text-xs text-muted-foreground">
              Version {health?.version || '...'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Requests</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {usage?.total_requests?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Total requests made
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tokens Used</CardTitle>
            <Code2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {usage?.total_tokens?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Input: {usage?.input_tokens?.toLocaleString() || 0} | Output: {usage?.output_tokens?.toLocaleString() || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cost</CardTitle>
            <span className="text-xs text-muted-foreground">USD</span>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${usage?.total_cost?.toFixed(4) || '0.0000'}
            </div>
            <p className="text-xs text-muted-foreground">
              Total API cost
            </p>
          </CardContent>
        </Card>
      </div>

      {/* RAG Status */}
      {ragStats && ragStats.total_chunks !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">RAG Index Status</CardTitle>
            <CardDescription>Codebase indexing for context-aware generation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Indexed Chunks</span>
                <span className="font-medium">{ragStats.total_chunks || 0}</span>
              </div>
              <Progress value={ragStats.total_chunks ? 100 : 0} className="h-2" />
              <p className="text-xs text-muted-foreground">
                {ragStats.indexed_files || 0} files indexed
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {quickActions.map((action) => (
            <Link key={action.to} to={action.to}>
              <Card className="hover:bg-accent transition-colors cursor-pointer h-full">
                <CardHeader className="flex flex-row items-center gap-4">
                  <div className={`p-2 rounded-lg bg-muted ${action.color}`}>
                    <action.icon className="h-6 w-6" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{action.title}</CardTitle>
                    <CardDescription>{action.description}</CardDescription>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* Capabilities */}
      {health?.capabilities && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Available Capabilities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {health.capabilities.map((cap) => (
                <span
                  key={cap}
                  className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary"
                >
                  {cap.replace('_', ' ')}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
