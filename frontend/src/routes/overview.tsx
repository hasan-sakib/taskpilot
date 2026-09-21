import { Bot, Database, ListChecks, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useApprovals } from '@/features/approvals/use-approvals'
import { useHealth } from '@/features/health/use-health'
import { useRuns } from '@/features/runs/use-runs'
import { formatRelativeTime } from '@/lib/format'
import { formatStatusLabel, isTerminalRunStatus, runStatusVariant } from '@/lib/status'

export function OverviewPage() {
  const { data: health } = useHealth()
  const { data: pendingApprovals, isError: approvalsError } = useApprovals({ status: 'pending' })
  const { data: runs, isError: runsError } = useRuns(10)

  const activeRun = runs?.find((run) => !isTerminalRunStatus(run.status))

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
            <Link to="/approvals" className="text-2xl font-semibold tabular-nums hover:underline">
              {approvalsError ? '!' : (pendingApprovals?.length ?? '—')}
            </Link>
            <CardDescription>
              {approvalsError
                ? 'Could not load'
                : pendingApprovals?.length
                  ? 'Awaiting your decision'
                  : 'Nothing waiting'}
            </CardDescription>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active run</CardTitle>
          <CardDescription>The currently executing agent run, if any.</CardDescription>
        </CardHeader>
        <CardContent>
          {runsError ? (
            <ErrorState description="Couldn't reach the backend to load runs. Try again shortly." />
          ) : activeRun ? (
            <Link
              to={`/agent?run=${activeRun.id}`}
              className="block space-y-2 rounded-md border border-border p-4 transition-colors hover:bg-accent/60"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium">{activeRun.goal}</p>
                <Badge variant={runStatusVariant(activeRun.status)}>
                  {formatStatusLabel(activeRun.status)}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Started {formatRelativeTime(activeRun.started_at)}
              </p>
            </Link>
          ) : (
            <EmptyState
              icon={Bot}
              title="No active run"
              description="Start a goal from the Agent tab to see live plan and task progress here."
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent runs</CardTitle>
          <CardDescription>The most recent agent runs across all goals.</CardDescription>
        </CardHeader>
        <CardContent>
          {runsError ? (
            <ErrorState description="Couldn't reach the backend to load runs. Try again shortly." />
          ) : runs && runs.length > 0 ? (
            <ul className="divide-y divide-border">
              {runs.slice(0, 5).map((run) => (
                <li key={run.id}>
                  <Link
                    to={`/agent?run=${run.id}`}
                    className="flex items-center justify-between gap-3 py-2.5 text-sm transition-colors hover:text-foreground"
                  >
                    <span className="truncate text-muted-foreground">{run.goal}</span>
                    <span className="flex shrink-0 items-center gap-2">
                      <Badge variant={runStatusVariant(run.status)}>
                        {formatStatusLabel(run.status)}
                      </Badge>
                      <span className="w-16 text-right text-xs text-muted-foreground">
                        {formatRelativeTime(run.created_at)}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={ListChecks}
              title="Nothing has run yet"
              description="Activity will appear here once you start your first agent run."
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
