import { ListChecks } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { TaskStatus } from '@/features/tasks/api'
import { useTasks } from '@/features/tasks/use-tasks'
import { useRuns } from '@/features/runs/use-runs'
import { formatRelativeTime } from '@/lib/format'
import { formatStatusLabel, taskStatusVariant } from '@/lib/status'

const TASK_STATUSES: TaskStatus[] = [
  'pending',
  'in_progress',
  'blocked_on_approval',
  'completed',
  'failed',
  'skipped',
  'cancelled',
]

export function TasksPage() {
  const [runId, setRunId] = useState<string>('all')
  const [status, setStatus] = useState<string>('all')
  const { data: runs } = useRuns(50)
  const { data: tasks, isLoading, isError } = useTasks(
    {
      run_id: runId === 'all' ? undefined : runId,
      status: status === 'all' ? undefined : (status as TaskStatus),
    },
    { poll: true },
  )

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4 space-y-0">
        <div>
          <CardTitle>Tasks</CardTitle>
          <CardDescription>Browse and filter tasks across all agent runs.</CardDescription>
        </div>
        <div className="flex gap-2">
          <Select value={runId} onValueChange={setRunId}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All runs" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All runs</SelectItem>
              {runs?.map((run) => (
                <SelectItem key={run.id} value={run.id}>
                  {run.goal.slice(0, 40)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {TASK_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {formatStatusLabel(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading tasks…</p>
        ) : isError ? (
          <ErrorState description="Couldn't reach the backend to load tasks. Try again shortly." />
        ) : !tasks || tasks.length === 0 ? (
          <EmptyState
            icon={ListChecks}
            title="No tasks found"
            description="Task list and board views will populate here once a run has a plan."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Tool</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Run</TableHead>
                <TableHead>Retries</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="max-w-xs">
                    <p className="truncate font-medium">{task.description}</p>
                    {task.dependencies.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        depends on {task.dependencies.length} task
                        {task.dependencies.length > 1 ? 's' : ''}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{task.tool_name}</TableCell>
                  <TableCell>
                    <Badge variant={taskStatusVariant(task.status)}>
                      {formatStatusLabel(task.status)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Link
                      to={`/agent?run=${task.run_id}`}
                      className="text-xs text-muted-foreground hover:text-foreground hover:underline"
                    >
                      {task.run_id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {task.retry_count}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatRelativeTime(task.updated_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
