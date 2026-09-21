import { apiClient } from '@/lib/api-client'

export interface OllamaStatus {
  reachable: boolean
  base_url: string
  model: string
  detail: string | null
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  database: boolean
  ollama: OllamaStatus
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health')
  return data
}
