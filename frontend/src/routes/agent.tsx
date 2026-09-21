import { Bot } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

import { EmptyState } from '@/components/layout/empty-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { GoalForm } from '@/features/runs/components/goal-form'
import { RunDetail } from '@/features/runs/components/run-detail'
import { RunPicker } from '@/features/runs/components/run-picker'

export function AgentPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedRunId = searchParams.get('run') ?? undefined

  function selectRun(runId: string) {
    setSearchParams({ run: runId })
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>New goal</CardTitle>
            <CardDescription>
              Describe an outcome — the agent plans and executes the steps, pausing for your
              approval before anything consequential.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GoalForm onRunCreated={selectRun} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent runs</CardTitle>
          </CardHeader>
          <CardContent>
            <RunPicker selectedRunId={selectedRunId} onSelect={selectRun} />
          </CardContent>
        </Card>
      </div>

      <div className="lg:col-span-3">
        {selectedRunId ? (
          <RunDetail runId={selectedRunId} />
        ) : (
          <Card>
            <CardContent className="pt-6">
              <EmptyState
                icon={Bot}
                title="No run selected"
                description="Start a new goal or pick a recent run from the left to see its plan, activity, and approvals."
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
