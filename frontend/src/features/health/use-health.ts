import { useQuery } from '@tanstack/react-query'

import { fetchHealth } from '@/features/health/api'

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
    retry: 1,
  })
}
