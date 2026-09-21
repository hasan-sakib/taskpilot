import axios, { isAxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 20_000,
})

// A submitted goal (and an approve/reject decision) is a synchronous, blocking call on
// the backend -- it runs the graph in-process until the next pause or terminal state,
// which can genuinely take minutes with a real local model. The default timeout above
// is tuned for ordinary reads/writes and would abort those calls prematurely.
export const LONG_RUNNING_TIMEOUT_MS = 600_000

export function getErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (error.code === 'ECONNABORTED') return 'The request timed out.'
    if (error.message) return error.message
  }
  return fallback
}
