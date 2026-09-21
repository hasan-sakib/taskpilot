import { Ban, Loader2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ErrorState } from '@/components/layout/error-state'
import { ApprovalCard } from '@/features/approvals/components/approval-card'
import { useApprovals } from '@/features/approvals/use-approvals'
import { EventLog } from '@/features/runs/components/event-log'
import { TaskTimeline } from '@/features/runs/components/task-timeline'
import { useCancelRun, useRun } from '@/features/runs/use-runs'
import { getErrorMessage } from '@/lib/api-client'
import { formatDateTime } from '@/lib/format'
import { formatStatusLabel, isTerminalRunStatus, runStatusVariant } from '@/lib/status'

interface RunDetailProps {
  runId: string
}

export function RunDetail({ runId }: RunDetailProps) {
  const { data: run, isLoading, isError, error } = useRun(runId)
  const cancelRun = useCancelRun()
  const { data: approvals } = useApprovals(
    { run_id: runId, status: 'pending' },
    { poll: run?.status === 'paused_for_approval' },
  )

  if (isError) {
    return <ErrorState description={getErrorMessage(error, "Couldn't load this run.")} />
  }

  if (isLoading || !run) {
    return <p className="text-sm text-muted-foreground">Loading run…</p>
  }

  const active = !isTerminalRunStatus(run.status)
  const canCancel = active && !run.cancel_requested

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
          <div className="space-y-1.5">
            <CardTitle className="text-base font-semibold text-foreground">{run.goal}</CardTitle>
            <CardDescription>
              {run.model_name ?? 'test provider'} · started {formatDateTime(run.started_at)}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {run.status === 'running' && <Loader2 className="size-4 animate-spin text-warning" />}
            <Badge variant={runStatusVariant(run.status)}>{formatStatusLabel(run.status)}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground sm:grid-cols-4">
            <div>
              <p className="text-muted-foreground/70">Plan version</p>
              <p className="font-medium text-foreground">{run.plan_version}</p>
            </div>
            <div>
              <p className="text-muted-foreground/70">Created</p>
              <p className="font-medium text-foreground">{formatDateTime(run.created_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground/70">Completed</p>
              <p className="font-medium text-foreground">{formatDateTime(run.completed_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground/70">Run ID</p>
              <p className="truncate font-mono font-medium text-foreground">{run.id}</p>
            </div>
          </div>

          {canCancel && (
            <Button
              variant="outline"
              size="sm"
              disabled={cancelRun.isPending}
              onClick={() => cancelRun.mutate(run.id)}
            >
              <Ban /> Cancel run
            </Button>
          )}
          {run.cancel_requested && active && (
            <p className="text-xs text-muted-foreground">
              Cancellation requested — will stop before the next task starts.
            </p>
          )}

          {run.final_report && (
            <>
              <Separator />
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Final report</p>
                <p className="whitespace-pre-wrap text-sm">{run.final_report}</p>
              </div>
            </>
          )}
          {run.error_message && (
            <>
              <Separator />
              <div className="space-y-1">
                <p className="text-xs font-medium text-destructive">Error</p>
                <p className="whitespace-pre-wrap text-sm text-destructive">{run.error_message}</p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {run.status === 'paused_for_approval' &&
        approvals?.map((approval) => <ApprovalCard key={approval.id} approval={approval} />)}

      <Card>
        <CardHeader>
          <CardTitle>Plan &amp; tasks</CardTitle>
        </CardHeader>
        <CardContent>
          <TaskTimeline runId={runId} active={active} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <EventLog runId={runId} active={active} />
        </CardContent>
      </Card>
    </div>
  )
}
