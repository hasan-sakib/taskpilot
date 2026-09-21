import { SquareStack } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function MemoryPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Memory</CardTitle>
        <CardDescription>Preferences the agent may use to inform future runs.</CardDescription>
      </CardHeader>
      <CardContent>
        <EmptyState
          icon={SquareStack}
          title="No preferences saved"
          description="Preferences are only stored here after you explicitly confirm them — nothing is inferred automatically from conversations."
        />
      </CardContent>
    </Card>
  )
}
