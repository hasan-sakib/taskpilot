import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderWithProviders, screen, waitFor } from '@/test/test-utils'

import { WorkspacePage } from './workspace'

describe('WorkspacePage', () => {
  it('lists root entries, navigates into a folder, and previews a file', async () => {
    const user = userEvent.setup()
    renderWithProviders(<WorkspacePage />)

    expect(await screen.findByText('documents')).toBeInTheDocument()
    expect(screen.getByText('notes.txt')).toBeInTheDocument()

    await user.click(screen.getByText('documents'))

    expect(await screen.findByText('readme.txt')).toBeInTheDocument()
    expect(screen.getByText('documents')).toBeInTheDocument() // breadcrumb segment

    await user.click(screen.getByText('readme.txt'))

    await waitFor(() => {
      expect(screen.getByText('hello from readme')).toBeInTheDocument()
    })
  })

  it('navigates back to root via the breadcrumb', async () => {
    const user = userEvent.setup()
    renderWithProviders(<WorkspacePage />, { route: '/workspace?path=documents' })

    expect(await screen.findByText('readme.txt')).toBeInTheDocument()

    await user.click(screen.getByText('root'))

    expect(await screen.findByText('notes.txt')).toBeInTheDocument()
  })
})
