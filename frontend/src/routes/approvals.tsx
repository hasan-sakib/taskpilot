import { ShieldCheck } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function ApprovalsPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Approvals</CardTitle>
        <CardDescription>
          Consequential actions the agent wants to take, awaiting your decision.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={ShieldCheck}
          title="No pending approvals"
          description="Approval requests for sending messages, submitting forms, running new scripts, or deleting files will appear here."
        />
      </CardContent>
    </Card>
  )
}
