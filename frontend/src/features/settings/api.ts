import { apiClient } from '@/lib/api-client'

export interface SettingsResponse {
  llm_provider: string
  ollama_base_url: string
  ollama_model: string
  workspace_root: string
  max_tasks_per_run: number
  max_retries_per_task: number
  max_replanning_attempts: number
  max_run_duration_seconds: number
  max_tool_calls_per_run: number
  approval_ttl_seconds: number
  search_provider: string
  browser_allowed_domains: string[]
  browser_headless: boolean
  python_runner_timeout_seconds: number
  python_runner_memory_limit_mb: number
  python_runner_cpu_limit: number
}

export async function fetchSettings(): Promise<SettingsResponse> {
  const { data } = await apiClient.get<SettingsResponse>('/settings')
  return data
}
