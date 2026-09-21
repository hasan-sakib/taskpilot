import { Bot, Database, ListChecks, ShieldCheck } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealth } from '@/features/health/use-health'

export function OverviewPage() {
  const { data: health } = useHealth()

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-muted-foreground">Database</CardTitle>
            <Database className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge variant={health?.database ? 'success' : 'destructive'}>
              {health?.database ? 'Connected' : 'Unavailable'}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-muted-foreground">Local model</CardTitle>
            <Bot className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-1">
            <Badge variant={health?.ollama.reachable ? 'success' : 'warning'}>
              {health?.ollama.reachable ? 'Connected' : 'Not reachable'}
            </Badge>
            <CardDescription>{health?.ollama.model ?? '—'}</CardDescription>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-0">
            <CardTitle className="text-muted-foreground">Pending approvals</CardTitle>
            <ShieldCheck className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold tabular-nums text-muted-foreground">—</p>
            <CardDescription>Not tracked yet</CardDescription>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active run</CardTitle>
          <CardDescription>The currently executing agent run, if any.</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Bot}
            title="No active run"
            description="Start a goal from the Agent tab to see live plan and task progress here."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
          <CardDescription>Task completions, failures, and approvals across runs.</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={ListChecks}
            title="Nothing has run yet"
            description="Activity will appear here once the agent execution engine is wired up."
          />
        </CardContent>
      </Card>
    </div>
  )
}
