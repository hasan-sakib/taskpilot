import { ExternalLink, Globe } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useBrowserSessions } from '@/features/browser/use-browser'
import { formatDateTime, formatRelativeTime } from '@/lib/format'
import { browserSessionStatusVariant, formatStatusLabel } from '@/lib/status'

export function BrowserPage() {
  const { data: sessions, isLoading, isError } = useBrowserSessions()

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4 space-y-0">
        <div>
          <CardTitle>Browser</CardTitle>
          <CardDescription>
            Live and past browser sessions the agent has used, with recent state.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/workspace?path=exports%2Fscreenshots">
            <ExternalLink /> View screenshots
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading sessions…</p>
        ) : isError ? (
          <ErrorState description="Couldn't reach the backend to load browser sessions. Try again shortly." />
        ) : !sessions || sessions.length === 0 ? (
          <EmptyState
            icon={Globe}
            title="No browser session active"
            description="Sessions the agent starts with the browser tools will be tracked here, along with their status and current URL."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Session</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Current URL</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Closed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.map((session) => (
                <TableRow key={session.id}>
                  <TableCell>
                    <Link
                      to={`/agent?run=${session.run_id}`}
                      className="font-mono text-xs hover:underline"
                    >
                      {session.id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell className="flex items-center gap-1.5">
                    <Badge variant={browserSessionStatusVariant(session.status)}>
                      {formatStatusLabel(session.status)}
                    </Badge>
                    {session.is_live && <Badge variant="success">Live</Badge>}
                  </TableCell>
                  <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                    {session.current_url ?? '—'}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {session.headless ? 'Headless' : 'Visible'}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatRelativeTime(session.started_at)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {session.closed_at ? formatDateTime(session.closed_at) : '—'}
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
