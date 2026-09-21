import { Circle, Settings as SettingsIcon } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import { navItems } from '@/app/nav-items'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useHealth } from '@/features/health/use-health'
import { useRuns } from '@/features/runs/use-runs'
import { formatStatusLabel, isTerminalRunStatus, runStatusVariant } from '@/lib/status'
import { cn } from '@/lib/utils'

export function Topbar() {
  const location = useLocation()
  const { data: health, isLoading } = useHealth()
  const { data: runs } = useRuns(10)
  const activeRun = runs?.find((run) => !isTerminalRunStatus(run.status))

  const currentTitle =
    navItems.find((item) =>
      item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path),
    )?.label ?? 'TaskPilot'

  const modelConnected = health?.ollama.reachable ?? false

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background px-6">
      <h1 className="text-sm font-semibold">{currentTitle}</h1>

      <div className="flex items-center gap-3">
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs text-muted-foreground">
              <Circle
                className={cn(
                  'size-2 fill-current',
                  isLoading
                    ? 'text-muted-foreground'
                    : modelConnected
                      ? 'text-success'
                      : 'text-destructive',
                )}
              />
              {isLoading ? 'Checking model…' : modelConnected ? 'Model connected' : 'Model offline'}
            </div>
          </TooltipTrigger>
          <TooltipContent>
            {health ? `${health.ollama.base_url} · ${health.ollama.model}` : 'Ollama status unknown'}
          </TooltipContent>
        </Tooltip>

        <Badge variant={activeRun ? runStatusVariant(activeRun.status) : 'secondary'}>
          {activeRun ? formatStatusLabel(activeRun.status) : 'Agent idle'}
        </Badge>

        <Button variant="ghost" size="icon" asChild>
          <Link to="/settings" aria-label="Settings">
            <SettingsIcon />
          </Link>
        </Button>
      </div>
    </header>
  )
}
