import { apiClient } from '@/lib/api-client'

export interface PreferenceResponse {
  id: string
  key: string
  value: unknown
  description: string | null
  confirmed_by_user: boolean
  available_to_future_runs: boolean
  created_at: string
  updated_at: string
}

export interface CreatePreferenceRequest {
  key: string
  value: unknown
  description?: string | null
  confirmed_by_user?: boolean
  available_to_future_runs?: boolean
}

export interface UpdatePreferenceRequest {
  value?: unknown
  description?: string | null
  confirmed_by_user?: boolean
  available_to_future_runs?: boolean
}

export async function fetchPreferences(): Promise<PreferenceResponse[]> {
  const { data } = await apiClient.get<PreferenceResponse[]>('/memory/preferences')
  return data
}

export async function createPreference(
  body: CreatePreferenceRequest,
): Promise<PreferenceResponse> {
  const { data } = await apiClient.post<PreferenceResponse>('/memory/preferences', body)
  return data
}

export async function updatePreference(
  id: string,
  body: UpdatePreferenceRequest,
): Promise<PreferenceResponse> {
  const { data } = await apiClient.patch<PreferenceResponse>(`/memory/preferences/${id}`, body)
  return data
}

export async function deletePreference(id: string): Promise<void> {
  await apiClient.delete(`/memory/preferences/${id}`)
}
