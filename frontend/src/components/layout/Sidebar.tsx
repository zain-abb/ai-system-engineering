import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  LayoutDashboard,
  Code2,
  TestTube2,
  Search,
  FileText,
  BookOpen,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/generate', icon: Code2, label: 'Generate Code' },
  { to: '/tests', icon: TestTube2, label: 'Generate Tests' },
  { to: '/review', icon: Search, label: 'Code Review' },
  { to: '/requirements', icon: FileText, label: 'Requirements' },
  { to: '/docs', icon: BookOpen, label: 'Documentation' },
  { to: '/evaluate', icon: Shield, label: 'Evaluate' },
]

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <div
      className={cn(
        'relative flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center border-b px-4">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Code2 className="h-6 w-6 text-primary" />
            <span className="font-bold text-lg">SE-Agent</span>
          </div>
        )}
        {collapsed && <Code2 className="h-6 w-6 text-primary mx-auto" />}
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 py-4">
        <nav className="space-y-1 px-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground',
                  collapsed && 'justify-center'
                )
              }
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <Separator className="my-4" />

        <nav className="px-2">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                'hover:bg-accent hover:text-accent-foreground',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground',
                collapsed && 'justify-center'
              )
            }
          >
            <Settings className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Settings</span>}
          </NavLink>
        </nav>
      </ScrollArea>

      {/* Collapse Toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute -right-3 top-20 z-10 h-6 w-6 rounded-full border bg-background shadow-sm"
        onClick={onToggle}
      >
        {collapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </Button>
    </div>
  )
}
