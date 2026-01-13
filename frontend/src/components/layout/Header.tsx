import { useQuery } from '@tanstack/react-query'
import { Moon, Sun, Activity, DollarSign } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { api } from '@/lib/api'

interface HeaderProps {
  darkMode: boolean
  onToggleDarkMode: () => void
}

export function Header({ darkMode, onToggleDarkMode }: HeaderProps) {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: api.getUsage,
    refetchInterval: 60000, // Refresh every minute
  })

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold">AI Software Engineering Assistant</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Status */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 text-sm">
                <Activity
                  className={`h-4 w-4 ${
                    health?.agent_ready ? 'text-green-500' : 'text-yellow-500'
                  }`}
                />
                <span className="text-muted-foreground">
                  {health?.status || 'Connecting...'}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                Agent: {health?.agent_ready ? 'Ready' : 'Not Ready'}
                <br />
                Version: {health?.version || 'Unknown'}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Usage */}
        {usage && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-2 text-sm">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    ${usage.total_cost?.toFixed(4) || '0.0000'}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  Tokens: {usage.total_tokens?.toLocaleString() || 0}
                  <br />
                  Requests: {usage.total_requests || 0}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        {/* Dark Mode Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleDarkMode}
          className="h-9 w-9"
        >
          {darkMode ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>
      </div>
    </header>
  )
}
