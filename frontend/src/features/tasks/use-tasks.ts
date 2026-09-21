import { useQuery } from '@tanstack/react-query'

import { type ListTasksParams, fetchTasks } from './api'

export function useTasks(params?: ListTasksParams, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ['tasks', params ?? {}],
    queryFn: () => fetchTasks(params),
    refetchInterval: options?.poll ? 3_000 : false,
  })
}
