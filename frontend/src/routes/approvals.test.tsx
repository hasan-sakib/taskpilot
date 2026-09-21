import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'

import { mockPendingApproval } from '@/test/msw/handlers'
import { server } from '@/test/msw/server'
import { renderWithProviders, screen, waitFor } from '@/test/test-utils'
import type { ApprovalResponse } from '@/features/approvals/api'

import { ApprovalsPage } from './approvals'

/** A stateful mock backend for one approval: GET reflects whatever the last
 * approve/reject call set, the way the real API would -- needed to actually prove
 * cache invalidation re-fetches and reflects the new state, not just that the mutation
 * fired. A test asserting only on the outgoing request would still pass even if
 * useInvalidateAfterResolve() were deleted entirely. */
function seedStatefulApprovalBackend() {
  let approval: ApprovalResponse = { ...mockPendingApproval }

  server.use(
    http.get('/api/v1/approvals', ({ request }) => {
      const status = new URL(request.url).searchParams.get('status')
      const matches = !status || approval.status === status
      return HttpResponse.json(matches ? [approval] : [])
    }),
    http.post('/api/v1/approvals/:id/approve', () => {
      approval = { ...approval, status: 'approved', resolved_by: 'tester' }
      return HttpResponse.json(approval)
    }),
    http.post('/api/v1/approvals/:id/reject', async ({ request }) => {
      const body = (await request.json()) as { rejection_reason?: string }
      approval = { ...approval, status: 'rejected', rejection_reason: body.rejection_reason ?? null }
      return HttpResponse.json(approval)
    }),
  )

  return {
    getRecordedStatus: () => approval.status,
    getRecordedRejectionReason: () => approval.rejection_reason,
  }
}

describe('ApprovalsPage', () => {
  it('shows a pending approval with its exact unredacted payload, approves it, and the list refreshes without it', async () => {
    seedStatefulApprovalBackend()

    const user = userEvent.setup()
    renderWithProviders(<ApprovalsPage />)

    expect(await screen.findByText('workspace.write_file')).toBeInTheDocument()
    // The action payload must be shown exactly, unredacted -- the approver needs the
    // real value to make an informed decision.
    expect(screen.getByText(/"path": "notes\.txt"/)).toBeInTheDocument()
    expect(screen.getByText(/"content": "hello"/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^approve$/i }))

    // Proves cache invalidation actually re-fetched and reflects the new state, not
    // just that the approve request fired.
    await waitFor(() => {
      expect(screen.queryByText('workspace.write_file')).not.toBeInTheDocument()
    })
    expect(screen.getByText('No approvals found')).toBeInTheDocument()
  })

  it('rejects with a typed reason and the list refreshes without it', async () => {
    const backend = seedStatefulApprovalBackend()

    const user = userEvent.setup()
    renderWithProviders(<ApprovalsPage />)

    expect(await screen.findByText('workspace.write_file')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^reject$/i }))
    await user.type(
      screen.getByPlaceholderText(/why are you rejecting/i),
      'not needed right now',
    )
    await user.click(screen.getByRole('button', { name: /confirm reject/i }))

    await waitFor(() => {
      expect(screen.queryByText('workspace.write_file')).not.toBeInTheDocument()
    })
    expect(screen.getByText('No approvals found')).toBeInTheDocument()

    // Confirms the rejection was actually recorded server-side (not just hidden
    // client-side) and carried the typed reason through.
    expect(backend.getRecordedStatus()).toBe('rejected')
    expect(backend.getRecordedRejectionReason()).toBe('not needed right now')
  })

  it('shows an empty state when there is nothing pending', async () => {
    renderWithProviders(<ApprovalsPage />)
    expect(await screen.findByText('No approvals found')).toBeInTheDocument()
  })
})
