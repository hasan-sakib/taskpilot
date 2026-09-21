import { apiClient } from '@/lib/api-client'

export interface WorkspaceEntry {
  name: string
  path: string
  is_dir: boolean
  size_bytes: number
  modified_at: string
}

export interface WorkspaceListing {
  path: string
  parent_path: string | null
  entries: WorkspaceEntry[]
}

export async function fetchWorkspaceEntries(path = ''): Promise<WorkspaceListing> {
  const { data } = await apiClient.get<WorkspaceListing>('/workspace/entries', {
    params: { path },
  })
  return data
}

export function workspaceFileUrl(path: string): string {
  return `/api/v1/workspace/file?path=${encodeURIComponent(path)}`
}

export async function fetchWorkspaceFileText(path: string): Promise<string> {
  const { data } = await apiClient.get<string>('/workspace/file', {
    params: { path },
    responseType: 'text',
    transformResponse: (value: string) => value,
  })
  return data
}
