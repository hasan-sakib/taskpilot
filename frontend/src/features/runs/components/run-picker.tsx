import { Bot } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useRuns } from '@/features/runs/use-runs'
import { formatRelativeTime } from '@/lib/format'
import { formatStatusLabel, runStatusVariant } from '@/lib/status'
import { cn } from '@/lib/utils'

interface RunPickerProps {
  selectedRunId: string | undefined
  onSelect: (runId: string) => void
}

export function RunPicker({ selectedRunId, onSelect }: RunPickerProps) {
  const { data: runs, isLoading, isError } = useRuns(20)

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading runs…</p>
  }

  if (isError) {
    return <ErrorState description="Couldn't reach the backend to load runs." />
  }

  if (!runs || runs.length === 0) {
    return (
      <EmptyState
        icon={Bot}
        title="No runs yet"
        description="Submit a goal above to start the first one."
      />
    )
  }

  return (
    <ScrollArea className="h-80">
      <ul className="space-y-1 pr-2">
        {runs.map((run) => (
          <li key={run.id}>
            <button
              type="button"
              onClick={() => onSelect(run.id)}
              className={cn(
                'w-full rounded-md border px-3 py-2 text-left text-sm transition-colors',
                run.id === selectedRunId
                  ? 'border-primary/40 bg-accent'
                  : 'border-transparent hover:bg-accent/60',
              )}
            >
              <p className="truncate font-medium">{run.goal}</p>
              <div className="mt-1 flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                <Badge variant={runStatusVariant(run.status)}>
                  {formatStatusLabel(run.status)}
                </Badge>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelativeTime(run.created_at)}
                </span>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </ScrollArea>
  )
}
