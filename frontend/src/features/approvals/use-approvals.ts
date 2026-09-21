import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { getErrorMessage } from '@/lib/api-client'

import { type ListApprovalsParams, approveApproval, fetchApprovals, rejectApproval } from './api'

export function useApprovals(params?: ListApprovalsParams, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ['approvals', params ?? {}],
    queryFn: () => fetchApprovals(params),
    refetchInterval: options?.poll === false ? false : 4_000,
  })
}

function useInvalidateAfterResolve() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['approvals'] })
    void queryClient.invalidateQueries({ queryKey: ['runs'] })
    void queryClient.invalidateQueries({ queryKey: ['tasks'] })
  }
}

export function useApproveApproval() {
  const invalidate = useInvalidateAfterResolve()
  return useMutation({
    mutationFn: ({ approvalId, resolvedBy }: { approvalId: string; resolvedBy?: string }) =>
      approveApproval(approvalId, resolvedBy),
    onSuccess: () => {
      invalidate()
      toast.success('Approved — the run has resumed')
    },
    onError: (error) => {
      toast.error('Could not approve', { description: getErrorMessage(error) })
    },
  })
}

export function useRejectApproval() {
  const invalidate = useInvalidateAfterResolve()
  return useMutation({
    mutationFn: ({
      approvalId,
      rejectionReason,
      resolvedBy,
    }: {
      approvalId: string
      rejectionReason?: string
      resolvedBy?: string
    }) => rejectApproval(approvalId, rejectionReason, resolvedBy),
    onSuccess: () => {
      invalidate()
      toast.success('Rejected — the run has resumed')
    },
    onError: (error) => {
      toast.error('Could not reject', { description: getErrorMessage(error) })
    },
  })
}
