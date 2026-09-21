import { apiClient, LONG_RUNNING_TIMEOUT_MS } from '@/lib/api-client'

export type RunStatus =
  | 'pending'
  | 'running'
  | 'paused_for_approval'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface RunResponse {
  id: string
  goal: string
  status: RunStatus
  plan_version: number
  model_name: string | null
  final_report: string | null
  error_message: string | null
  cancel_requested: boolean
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface EventSeverityPayload {
  id: string
  run_id: string
  task_id: string | null
  event_type: string
  node_name: string | null
  payload: Record<string, unknown>
  severity: 'debug' | 'info' | 'warning' | 'error'
  created_at: string
}

export interface CreateRunRequest {
  goal: string
  llm_provider?: 'ollama' | 'test'
}

export async function fetchRuns(limit = 50): Promise<RunResponse[]> {
  const { data } = await apiClient.get<RunResponse[]>('/agent/runs', { params: { limit } })
  return data
}

export async function fetchRun(runId: string): Promise<RunResponse> {
  const { data } = await apiClient.get<RunResponse>(`/agent/runs/${runId}`)
  return data
}

export async function fetchRunEvents(runId: string): Promise<EventSeverityPayload[]> {
  const { data } = await apiClient.get<EventSeverityPayload[]>(`/agent/runs/${runId}/events`)
  return data
}

export async function createRun(body: CreateRunRequest): Promise<RunResponse> {
  const { data } = await apiClient.post<RunResponse>('/agent/runs', body, {
    timeout: LONG_RUNNING_TIMEOUT_MS,
  })
  return data
}

export async function cancelRun(runId: string): Promise<RunResponse> {
  const { data } = await apiClient.post<RunResponse>(`/agent/runs/${runId}/cancel`)
  return data
}
