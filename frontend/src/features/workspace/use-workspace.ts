import { useQuery } from '@tanstack/react-query'

import { fetchWorkspaceEntries, fetchWorkspaceFileText } from './api'

export function useWorkspaceEntries(path: string) {
  return useQuery({
    queryKey: ['workspace', 'entries', path],
    queryFn: () => fetchWorkspaceEntries(path),
  })
}

export function useWorkspaceFileText(path: string | undefined) {
  return useQuery({
    queryKey: ['workspace', 'file', path],
    queryFn: () => fetchWorkspaceFileText(path!),
    enabled: !!path,
  })
}
