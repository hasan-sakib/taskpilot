import { AlertCircle, CheckCircle2, CircleDashed, Loader2, SkipForward, XCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import type { AgentTaskResponse, TaskStatus } from '@/features/tasks/api'
import { useTasks } from '@/features/tasks/use-tasks'
import { cn } from '@/lib/utils'
import { formatStatusLabel, taskStatusVariant } from '@/lib/status'

const STATUS_ICONS: Record<TaskStatus, LucideIcon> = {
  pending: CircleDashed,
  ready: CircleDashed,
  in_progress: Loader2,
  blocked_on_approval: AlertCircle,
  completed: CheckCircle2,
  failed: XCircle,
  skipped: SkipForward,
  cancelled: XCircle,
}

interface TaskTimelineProps {
  runId: string
  active: boolean
}

export function TaskTimeline({ runId, active }: TaskTimelineProps) {
  const { data: tasks, isLoading, isError } = useTasks({ run_id: runId }, { poll: active })

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading tasks…</p>
  }

  if (isError) {
    return <ErrorState description="Couldn't load tasks for this run." />
  }

  if (!tasks || tasks.length === 0) {
    return (
      <EmptyState
        icon={CircleDashed}
        title="No tasks planned yet"
        description="Tasks will appear here once the agent produces a plan for this run."
      />
    )
  }

  const sorted = [...tasks].sort((a, b) => a.sequence_index - b.sequence_index)

  return (
    <ol className="space-y-2">
      {sorted.map((task) => (
        <TaskRow key={task.id} task={task} />
      ))}
    </ol>
  )
}

function TaskRow({ task }: { task: AgentTaskResponse }) {
  const Icon = STATUS_ICONS[task.status]
  return (
    <li className="flex items-start gap-3 rounded-md border border-border p-3">
      <Icon
        className={cn(
          'mt-0.5 size-4 shrink-0 text-muted-foreground',
          task.status === 'in_progress' && 'animate-spin text-warning',
          task.status === 'completed' && 'text-success',
          task.status === 'failed' && 'text-destructive',
        )}
      />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{task.description}</span>
          <Badge variant={taskStatusVariant(task.status)}>{formatStatusLabel(task.status)}</Badge>
          {task.retry_count > 0 && (
            <span className="text-xs text-muted-foreground">retry {task.retry_count}</span>
          )}
        </div>
        <p className="font-mono text-xs text-muted-foreground">{task.tool_name}</p>
        {task.result_summary && (
          <p className="truncate text-xs text-muted-foreground">{task.result_summary}</p>
        )}
        {task.error_message && (
          <p className="text-xs text-destructive">{task.error_message}</p>
        )}
      </div>
    </li>
  )
}
