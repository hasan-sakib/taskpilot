import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from '@/components/layout/app-shell'
import { AgentPage } from '@/routes/agent'
import { ApprovalsPage } from '@/routes/approvals'
import { BrowserPage } from '@/routes/browser'
import { MemoryPage } from '@/routes/memory'
import { OverviewPage } from '@/routes/overview'
import { SettingsPage } from '@/routes/settings'
import { TasksPage } from '@/routes/tasks'
import { WorkspacePage } from '@/routes/workspace'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <OverviewPage /> },
      { path: '/agent', element: <AgentPage /> },
      { path: '/tasks', element: <TasksPage /> },
      { path: '/approvals', element: <ApprovalsPage /> },
      { path: '/browser', element: <BrowserPage /> },
      { path: '/workspace', element: <WorkspacePage /> },
      { path: '/memory', element: <MemoryPage /> },
      { path: '/settings', element: <SettingsPage /> },
    ],
  },
])
