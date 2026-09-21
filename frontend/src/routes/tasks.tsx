import { ListChecks } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function TasksPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tasks</CardTitle>
        <CardDescription>Browse and manage tasks across all agent runs.</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={ListChecks}
          title="No tasks yet"
          description="Task list and board views will populate here once the task management tools are implemented."
        />
      </CardContent>
    </Card>
  )
}
