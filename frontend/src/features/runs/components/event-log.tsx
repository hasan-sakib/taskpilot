import { Activity } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useRunEvents } from '@/features/runs/use-runs'
import { cn } from '@/lib/utils'
import { formatDateTime } from '@/lib/format'

interface EventLogProps {
  runId: string
  active: boolean
}

export function EventLog({ runId, active }: EventLogProps) {
  const { data: events, isLoading, isError } = useRunEvents(runId, { active })

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading activity…</p>
  }

  if (isError) {
    return <ErrorState description="Couldn't load activity for this run." />
  }

  if (!events || events.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No activity yet"
        description="Node transitions, tool calls, and retries will be logged here as the run progresses."
      />
    )
  }

  return (
    <ScrollArea className="h-64 rounded-md border border-border">
      <ul className="divide-y divide-border">
        {events.map((event) => (
          <li key={event.id} className="flex items-start gap-3 px-3 py-2 text-xs">
            <span className="shrink-0 whitespace-nowrap text-muted-foreground">
              {formatDateTime(event.created_at)}
            </span>
            <span
              className={cn(
                'shrink-0 font-mono',
                event.severity === 'error' && 'text-destructive',
                event.severity === 'warning' && 'text-warning',
              )}
            >
              {event.node_name ?? '—'}
            </span>
            <span className="min-w-0 flex-1 truncate text-foreground">{event.event_type}</span>
          </li>
        ))}
      </ul>
    </ScrollArea>
  )
}
