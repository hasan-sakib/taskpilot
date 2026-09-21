import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { getErrorMessage } from '@/lib/api-client'
import { isTerminalRunStatus } from '@/lib/status'

import {
  type CreateRunRequest,
  cancelRun,
  createRun,
  fetchRun,
  fetchRunEvents,
  fetchRuns,
} from './api'

export function useRuns(limit = 50) {
  return useQuery({
    queryKey: ['runs', { limit }],
    queryFn: () => fetchRuns(limit),
    refetchInterval: 5_000,
  })
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: () => fetchRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && isTerminalRunStatus(status) ? false : 3_000
    },
  })
}

export function useRunEvents(runId: string | undefined, options?: { active?: boolean }) {
  return useQuery({
    queryKey: ['runs', runId, 'events'],
    queryFn: () => fetchRunEvents(runId!),
    enabled: !!runId,
    refetchInterval: options?.active ? 2_000 : false,
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateRunRequest) => createRun(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['runs'] })
      void queryClient.invalidateQueries({ queryKey: ['tasks'] })
      void queryClient.invalidateQueries({ queryKey: ['approvals'] })
    },
    onError: (error) => {
      toast.error('Could not start the run', { description: getErrorMessage(error) })
    },
  })
}

export function useCancelRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => cancelRun(runId),
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ['runs'] })
      toast.success(`Cancellation requested for run ${run.id.slice(0, 8)}`)
    },
    onError: (error) => {
      toast.error('Could not cancel the run', { description: getErrorMessage(error) })
    },
  })
}
