import { Globe } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function BrowserPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Browser</CardTitle>
        <CardDescription>Live browser session status, screenshots, and recent actions.</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={Globe}
          title="No browser session active"
          description="Playwright-driven browser automation lands in Phase 3 of the build."
        />
      </CardContent>
    </Card>
  )
}
