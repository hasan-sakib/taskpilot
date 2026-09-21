import { Bot } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function AgentPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent workspace</CardTitle>
        <CardDescription>
          Submit a goal, watch the plan execute, and respond to approvals in real time.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={Bot}
          title="Agent execution engine not yet connected"
          description="The LangGraph run endpoint lands in Phase 2 of the build. This screen will host goal input, run controls, live task timeline, and the final report."
        />
      </CardContent>
    </Card>
  )
}
