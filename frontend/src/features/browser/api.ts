import { apiClient } from '@/lib/api-client'

export type BrowserSessionStatus = 'active' | 'closed' | 'crashed'

export interface BrowserSessionResponse {
  id: string
  run_id: string
  task_id: string | null
  status: BrowserSessionStatus
  current_url: string | null
  headless: boolean
  started_at: string | null
  closed_at: string | null
  is_live: boolean
}

export async function fetchBrowserSessions(runId?: string): Promise<BrowserSessionResponse[]> {
  const { data } = await apiClient.get<BrowserSessionResponse[]>('/browser/sessions', {
    params: runId ? { run_id: runId } : undefined,
  })
  return data
}
