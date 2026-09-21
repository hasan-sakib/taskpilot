import { useQuery } from '@tanstack/react-query'

import { fetchBrowserSessions } from './api'

export function useBrowserSessions(runId?: string) {
  return useQuery({
    queryKey: ['browser-sessions', runId ?? null],
    queryFn: () => fetchBrowserSessions(runId),
    refetchInterval: 10_000,
  })
}
