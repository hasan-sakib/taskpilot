import { ShieldCheck } from 'lucide-react'
import { useState } from 'react'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ApprovalCard } from '@/features/approvals/components/approval-card'
import type { ApprovalStatus } from '@/features/approvals/api'
import { useApprovals } from '@/features/approvals/use-approvals'

const STATUS_OPTIONS: { value: ApprovalStatus | 'all'; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'all', label: 'All' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'expired', label: 'Expired' },
]

export function ApprovalsPage() {
  const [status, setStatus] = useState<ApprovalStatus | 'all'>('pending')
  const { data: approvals, isLoading, isError } = useApprovals(
    status === 'all' ? undefined : { status },
  )

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4 space-y-0">
        <div>
          <CardTitle>Approvals</CardTitle>
          <CardDescription>
            Consequential actions the agent wants to take, awaiting your decision.
          </CardDescription>
        </div>
        <Select value={status} onValueChange={(value) => setStatus(value as ApprovalStatus | 'all')}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading approvals…</p>
        ) : isError ? (
          <ErrorState description="Couldn't reach the backend to load approvals. Try again shortly." />
        ) : !approvals || approvals.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="No approvals found"
            description="Approval requests for sending messages, submitting forms, running new scripts, or deleting files will appear here."
          />
        ) : (
          <div className="space-y-3">
            {approvals.map((approval) => (
              <ApprovalCard key={approval.id} approval={approval} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
