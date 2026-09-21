import axios, { isAxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 20_000,
})

// A submitted goal (and an approve/reject decision) is a synchronous, blocking call on
// the backend -- it runs the graph in-process until the next pause or terminal state.
// The backend's own ceiling for that (task_selection.py checks elapsed time against
// Settings.max_run_duration_seconds every cycle) is configurable and defaults to 30
// minutes, not something a hardcoded frontend constant should guess at: a real
// integration run against qwen3:4b hit a hardcoded 10-minute client timeout while the
// backend was still genuinely working (confirmed still "running" server-side well
// past that point) -- the UI reported a false failure for a run that was actually
// fine. This derives the client timeout from the backend's real configured value
// instead, with a margin for response/network overhead on top of the graph's own
// internal deadline.
const FALLBACK_LONG_RUNNING_TIMEOUT_MS = 600_000
const LONG_RUNNING_TIMEOUT_MARGIN_MS = 30_000
let cachedMaxRunDurationMs: number | undefined

export async function getLongRunningTimeoutMs(): Promise<number> {
  if (cachedMaxRunDurationMs !== undefined) {
    return cachedMaxRunDurationMs
  }
  try {
    // Settings are static environment config for the lifetime of a backend process
    // (see app/core/config.py) -- fetching and caching once is safe, and avoids a
    // circular dependency on the settings feature module's own React Query hook.
    const { data } = await apiClient.get<{ max_run_duration_seconds: number }>('/settings')
    cachedMaxRunDurationMs = data.max_run_duration_seconds * 1000 + LONG_RUNNING_TIMEOUT_MARGIN_MS
    return cachedMaxRunDurationMs
  } catch {
    // Deliberately not cached: a transient failure here (e.g. the backend still
    // starting up when this fires) shouldn't permanently lock the rest of the session
    // into the fallback once /settings would actually succeed on a later call.
    return FALLBACK_LONG_RUNNING_TIMEOUT_MS
  }
}

export function getErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (error.code === 'ECONNABORTED') return 'The request timed out.'
    if (error.message) return error.message
  }
  return fallback
}
