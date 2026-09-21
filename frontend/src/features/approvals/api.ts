import { apiClient, LONG_RUNNING_TIMEOUT_MS } from '@/lib/api-client'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'invalidated'

export interface ApprovalResponse {
  id: string
  run_id: string
  task_id: string
  action_type: string
  target: string | null
  action_payload: Record<string, unknown>
  payload_hash: string
  status: ApprovalStatus
  requested_at: string
  expires_at: string
  resolved_at: string | null
  resolved_by: string | null
  rejection_reason: string | null
}

export interface ListApprovalsParams {
  status?: ApprovalStatus
  run_id?: string
}

export async function fetchApprovals(params?: ListApprovalsParams): Promise<ApprovalResponse[]> {
  const { data } = await apiClient.get<ApprovalResponse[]>('/approvals', { params })
  return data
}

export async function fetchApproval(approvalId: string): Promise<ApprovalResponse> {
  const { data } = await apiClient.get<ApprovalResponse>(`/approvals/${approvalId}`)
  return data
}

export async function approveApproval(
  approvalId: string,
  resolvedBy?: string,
): Promise<ApprovalResponse> {
  const { data } = await apiClient.post<ApprovalResponse>(
    `/approvals/${approvalId}/approve`,
    { resolved_by: resolvedBy || undefined },
    { timeout: LONG_RUNNING_TIMEOUT_MS },
  )
  return data
}

export async function rejectApproval(
  approvalId: string,
  rejectionReason?: string,
  resolvedBy?: string,
): Promise<ApprovalResponse> {
  const { data } = await apiClient.post<ApprovalResponse>(
    `/approvals/${approvalId}/reject`,
    { resolved_by: resolvedBy || undefined, rejection_reason: rejectionReason || undefined },
    { timeout: LONG_RUNNING_TIMEOUT_MS },
  )
  return data
}
