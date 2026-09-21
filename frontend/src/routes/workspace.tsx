import { FolderOpen } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function WorkspacePage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Workspace</CardTitle>
        <CardDescription>Files and folders the agent creates and organizes.</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={FolderOpen}
          title="Workspace explorer not yet connected"
          description="File browsing, preview, and organization tools land alongside the workspace tools in Phase 3."
        />
      </CardContent>
    </Card>
  )
}
