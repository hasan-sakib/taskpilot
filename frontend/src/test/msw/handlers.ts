import { HttpResponse, http } from 'msw'

const BASE = '/api/v1'

export const mockRun = {
  id: 'run-1',
  goal: 'Research something interesting',
  status: 'completed' as const,
  plan_version: 1,
  model_name: 'qwen3:4b',
  final_report: 'Done.',
  error_message: null,
  cancel_requested: false,
  created_at: '2026-01-01T00:00:00',
  started_at: '2026-01-01T00:00:01',
  completed_at: '2026-01-01T00:00:30',
}

export const mockPendingApproval = {
  id: 'approval-1',
  run_id: 'run-1',
  task_id: 'task-1',
  action_type: 'workspace.write_file',
  target: null,
  action_payload: { path: 'notes.txt', content: 'hello' },
  payload_hash: 'hash-1',
  status: 'pending' as const,
  requested_at: '2026-01-01T00:00:00',
  expires_at: '2026-01-01T00:15:00',
  resolved_at: null,
  resolved_by: null,
  rejection_reason: null,
}

export const handlers = [
  http.get(`${BASE}/health`, () =>
    HttpResponse.json({
      status: 'ok',
      database: true,
      ollama: { reachable: true, base_url: 'http://localhost:11434', model: 'qwen3:4b', detail: null },
    }),
  ),

  http.get(`${BASE}/settings`, () =>
    HttpResponse.json({
      llm_provider: 'ollama',
      ollama_base_url: 'http://localhost:11434',
      ollama_model: 'qwen3:4b',
      workspace_root: '/workspace',
      max_tasks_per_run: 25,
      max_retries_per_task: 3,
      max_replanning_attempts: 3,
      max_run_duration_seconds: 1800,
      max_tool_calls_per_run: 100,
      approval_ttl_seconds: 900,
      search_provider: 'duckduckgo',
      browser_allowed_domains: [],
      browser_headless: false,
      python_runner_timeout_seconds: 60,
      python_runner_memory_limit_mb: 512,
      python_runner_cpu_limit: 1,
    }),
  ),

  http.get(`${BASE}/agent/runs`, () => HttpResponse.json([mockRun])),
  http.get(`${BASE}/agent/runs/:id`, () => HttpResponse.json(mockRun)),
  http.get(`${BASE}/agent/runs/:id/events`, () => HttpResponse.json([])),
  http.post(`${BASE}/agent/runs`, () => HttpResponse.json(mockRun, { status: 201 })),

  http.get(`${BASE}/tasks`, () => HttpResponse.json([])),

  http.get(`${BASE}/approvals`, () => HttpResponse.json([])),
  http.get(`${BASE}/approvals/:id`, () => HttpResponse.json(mockPendingApproval)),
  http.post(`${BASE}/approvals/:id/approve`, () =>
    HttpResponse.json({ ...mockPendingApproval, status: 'approved', resolved_by: 'tester' }),
  ),
  http.post(`${BASE}/approvals/:id/reject`, () =>
    HttpResponse.json({ ...mockPendingApproval, status: 'rejected' }),
  ),

  http.get(`${BASE}/browser/sessions`, () => HttpResponse.json([])),

  http.get(`${BASE}/memory/preferences`, () => HttpResponse.json([])),

  http.get(`${BASE}/workspace/entries`, ({ request }) => {
    const path = new URL(request.url).searchParams.get('path') || ''
    if (path === 'documents') {
      return HttpResponse.json({
        path: 'documents',
        parent_path: '',
        entries: [
          { name: 'readme.txt', path: 'documents/readme.txt', is_dir: false, size_bytes: 11, modified_at: '2026-01-01T00:00:00' },
        ],
      })
    }
    return HttpResponse.json({
      path: '.',
      parent_path: null,
      entries: [
        { name: 'documents', path: 'documents', is_dir: true, size_bytes: 0, modified_at: '2026-01-01T00:00:00' },
        { name: 'notes.txt', path: 'notes.txt', is_dir: false, size_bytes: 5, modified_at: '2026-01-01T00:00:00' },
      ],
    })
  }),
  http.get(`${BASE}/workspace/file`, ({ request }) => {
    const path = new URL(request.url).searchParams.get('path')
    if (path === 'documents/readme.txt') {
      return HttpResponse.text('hello from readme', {
        headers: { 'Content-Type': 'text/plain' },
      })
    }
    return HttpResponse.text('hello world', { headers: { 'Content-Type': 'text/plain' } })
  }),
]
