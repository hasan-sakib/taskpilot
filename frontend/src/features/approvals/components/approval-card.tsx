import { AlertTriangle, Check, X } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import type { ApprovalResponse } from '@/features/approvals/api'
import { useApproveApproval, useRejectApproval } from '@/features/approvals/use-approvals'
import { formatDateTime, formatRelativeTime } from '@/lib/format'

interface ApprovalCardProps {
  approval: ApprovalResponse
}

export function ApprovalCard({ approval }: ApprovalCardProps) {
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const approve = useApproveApproval()
  const reject = useRejectApproval()

  const isPending = approval.status === 'pending'
  const isBusy = approve.isPending || reject.isPending

  return (
    <Card className="border-warning/40">
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-4 text-warning" />
            <span className="font-mono text-sm font-medium">{approval.action_type}</span>
          </div>
          {approval.target && (
            <p className="text-xs text-muted-foreground">Target: {approval.target}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Requested {formatRelativeTime(approval.requested_at)} · expires{' '}
            {formatRelativeTime(approval.expires_at)}
          </p>
        </div>
        <Badge variant="warning">Awaiting decision</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
          {JSON.stringify(approval.action_payload, null, 2)}
        </pre>

        {isPending && (
          <>
            {showRejectForm && (
              <Textarea
                autoFocus
                placeholder="Why are you rejecting this action? (optional)"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="text-sm"
              />
            )}
            <div className="flex flex-wrap justify-end gap-2">
              {showRejectForm ? (
                <>
                  <Button variant="ghost" size="sm" onClick={() => setShowRejectForm(false)}>
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={isBusy}
                    onClick={() =>
                      reject.mutate({ approvalId: approval.id, rejectionReason })
                    }
                  >
                    <X /> Confirm reject
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isBusy}
                    onClick={() => setShowRejectForm(true)}
                  >
                    <X /> Reject
                  </Button>
                  <Button
                    size="sm"
                    disabled={isBusy}
                    onClick={() => approve.mutate({ approvalId: approval.id })}
                  >
                    <Check /> Approve
                  </Button>
                </>
              )}
            </div>
          </>
        )}

        {!isPending && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {approval.status === 'approved' && `Approved by ${approval.resolved_by || 'you'}`}
              {approval.status === 'rejected' &&
                `Rejected${approval.rejection_reason ? `: ${approval.rejection_reason}` : ''}`}
              {approval.status === 'expired' && 'Expired without a decision'}
              {approval.status === 'invalidated' && 'Invalidated'}
            </span>
            <span>{formatDateTime(approval.resolved_at)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
