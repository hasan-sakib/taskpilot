import { apiClient } from '@/lib/api-client'

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'blocked_on_approval'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'cancelled'

export interface TaskDependencyResponse {
  depends_on_task_id: string
}

export interface AgentTaskResponse {
  id: string
  run_id: string
  plan_version: number
  sequence_index: number
  description: string
  tool_name: string
  tool_args: Record<string, unknown>
  status: TaskStatus
  priority: number
  deadline: string | null
  retry_count: number
  result_summary: string | null
  error_message: string | null
  parent_task_id: string | null
  dependencies: TaskDependencyResponse[]
  created_at: string
  updated_at: string
}

export interface ListTasksParams {
  run_id?: string
  status?: TaskStatus
}

export async function fetchTasks(params?: ListTasksParams): Promise<AgentTaskResponse[]> {
  const { data } = await apiClient.get<AgentTaskResponse[]>('/tasks', { params })
  return data
}
