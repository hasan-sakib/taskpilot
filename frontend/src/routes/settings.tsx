import { RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { useHealth } from '@/features/health/use-health'
import { useSettings } from '@/features/settings/use-settings'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  )
}

export function SettingsPage() {
  const { data: health, isFetching, refetch } = useHealth()
  const { data: settings } = useSettings()

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Local model</CardTitle>
            <CardDescription>Configured via the backend&apos;s environment settings.</CardDescription>
          </div>
          <Button variant="outline" size="sm" disabled={isFetching} onClick={() => refetch()}>
            <RefreshCw className={isFetching ? 'animate-spin' : undefined} /> Test connection
          </Button>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Row label="Ollama endpoint" value={health?.ollama.base_url ?? '—'} />
          <Separator />
          <Row label="Model" value={health?.ollama.model ?? '—'} />
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Connection</span>
            <Badge variant={health?.ollama.reachable ? 'success' : 'destructive'}>
              {health?.ollama.reachable ? 'Reachable' : 'Not reachable'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Execution limits</CardTitle>
          <CardDescription>
            Guardrails enforced by the backend on every run — editable via the .env file only.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Row label="Max tasks per run" value={settings?.max_tasks_per_run ?? '—'} />
          <Separator />
          <Row label="Max retries per task" value={settings?.max_retries_per_task ?? '—'} />
          <Separator />
          <Row label="Max replanning attempts" value={settings?.max_replanning_attempts ?? '—'} />
          <Separator />
          <Row
            label="Max run duration"
            value={settings ? `${settings.max_run_duration_seconds}s` : '—'}
          />
          <Separator />
          <Row label="Max tool calls per run" value={settings?.max_tool_calls_per_run ?? '—'} />
          <Separator />
          <Row
            label="Approval expiry"
            value={settings ? `${settings.approval_ttl_seconds}s` : '—'}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Browser &amp; script permissions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground">Allowed browser domains</span>
            <span className="text-right font-mono">
              {settings?.browser_allowed_domains.length
                ? settings.browser_allowed_domains.join(', ')
                : 'All domains'}
            </span>
          </div>
          <Separator />
          <Row label="Browser mode" value={settings?.browser_headless ? 'Headless' : 'Visible'} />
          <Separator />
          <Row label="Search provider" value={settings?.search_provider ?? '—'} />
          <Separator />
          <Row
            label="Script timeout"
            value={settings ? `${settings.python_runner_timeout_seconds}s` : '—'}
          />
          <Separator />
          <Row
            label="Script memory limit"
            value={settings ? `${settings.python_runner_memory_limit_mb} MB` : '—'}
          />
          <Separator />
          <Row label="Script CPU limit" value={settings?.python_runner_cpu_limit ?? '—'} />
          <Separator />
          <Row label="Workspace location" value={settings?.workspace_root ?? '—'} />
        </CardContent>
      </Card>
    </div>
  )
}
