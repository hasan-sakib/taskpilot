import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { useHealth } from '@/features/health/use-health'

export function SettingsPage() {
  const { data: health } = useHealth()

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Local model</CardTitle>
          <CardDescription>Configured via the backend&apos;s environment settings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Ollama endpoint</span>
            <span className="font-mono">{health?.ollama.base_url ?? '—'}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Model</span>
            <span className="font-mono">{health?.ollama.model ?? '—'}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Connection</span>
            <span>{health?.ollama.reachable ? 'Reachable' : 'Not reachable'}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Execution limits, browser domains &amp; script permissions</CardTitle>
          <CardDescription>
            Editable settings management is implemented in a later phase, alongside the
            settings API. Values currently come from the backend&apos;s .env configuration only.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
