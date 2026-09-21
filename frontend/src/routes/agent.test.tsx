import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'

import { mockRun } from '@/test/msw/handlers'
import { server } from '@/test/msw/server'
import { renderWithProviders, screen, waitFor, within } from '@/test/test-utils'

import { AgentPage } from './agent'

describe('AgentPage', () => {
  it('submits a goal and shows the created run once it settles', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AgentPage />)

    const textarea = screen.getByPlaceholderText(/e\.g\. Research remote frontend/i)
    await user.type(textarea, 'Research something interesting')
    await user.click(screen.getByRole('button', { name: /start run/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: mockRun.goal })).toBeInTheDocument()
    })

    const runDetail = screen.getByRole('heading', { name: mockRun.goal }).closest('div')!
    expect(within(runDetail.parentElement!).getByText(/completed/i)).toBeInTheDocument()
  })

  it('shows an error toast and does not navigate away when the goal fails to submit', async () => {
    server.use(
      http.post('/api/v1/agent/runs', () =>
        HttpResponse.json({ detail: 'Ollama is unreachable' }, { status: 502 }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(<AgentPage />)

    const textarea = screen.getByPlaceholderText(/e\.g\. Research remote frontend/i)
    await user.type(textarea, 'Research something interesting')
    await user.click(screen.getByRole('button', { name: /start run/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start run/i })).not.toBeDisabled()
    })
    expect(screen.getByText('No run selected')).toBeInTheDocument()
  })

  it('pre-selects a run from the URL and renders its plan section', async () => {
    renderWithProviders(<AgentPage />, { route: `/agent?run=${mockRun.id}` })

    expect(await screen.findByRole('heading', { name: mockRun.goal })).toBeInTheDocument()
    expect(screen.getByText('Plan & tasks')).toBeInTheDocument()
  })
})
