import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { getErrorMessage } from '@/lib/api-client'

import {
  type CreatePreferenceRequest,
  type UpdatePreferenceRequest,
  createPreference,
  deletePreference,
  fetchPreferences,
  updatePreference,
} from './api'

export function usePreferences() {
  return useQuery({
    queryKey: ['preferences'],
    queryFn: fetchPreferences,
  })
}

export function useCreatePreference() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreatePreferenceRequest) => createPreference(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['preferences'] })
      toast.success('Preference saved')
    },
    onError: (error) => {
      toast.error('Could not save preference', { description: getErrorMessage(error) })
    },
  })
}

export function useUpdatePreference() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdatePreferenceRequest }) =>
      updatePreference(id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['preferences'] })
      toast.success('Preference updated')
    },
    onError: (error) => {
      toast.error('Could not update preference', { description: getErrorMessage(error) })
    },
  })
}

export function useDeletePreference() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deletePreference(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['preferences'] })
      toast.success('Preference deleted')
    },
    onError: (error) => {
      toast.error('Could not delete preference', { description: getErrorMessage(error) })
    },
  })
}
