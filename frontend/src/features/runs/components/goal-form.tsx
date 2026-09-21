import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, Send } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useCreateRun } from '@/features/runs/use-runs'

const goalFormSchema = z.object({
  goal: z
    .string()
    .min(1, 'Describe what you want the agent to do')
    .max(4000, 'Keep it under 4000 characters'),
  llm_provider: z.enum(['ollama', 'test']),
})

type GoalFormValues = z.infer<typeof goalFormSchema>

interface GoalFormProps {
  onRunCreated: (runId: string) => void
}

export function GoalForm({ onRunCreated }: GoalFormProps) {
  const createRun = useCreateRun()
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<GoalFormValues>({
    resolver: zodResolver(goalFormSchema),
    defaultValues: { goal: '', llm_provider: 'ollama' },
  })

  const provider = watch('llm_provider')

  const onSubmit = handleSubmit(async (values) => {
    try {
      const run = await createRun.mutateAsync(values)
      reset()
      onRunCreated(run.id)
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  })

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="space-y-1.5">
        <Label htmlFor="goal">What should the agent do?</Label>
        <Textarea
          id="goal"
          rows={4}
          placeholder="e.g. Research remote frontend engineer roles at Series B startups and save a shortlist to the workspace."
          disabled={createRun.isPending}
          {...register('goal')}
        />
        {errors.goal && <p className="text-xs text-destructive">{errors.goal.message}</p>}
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="provider">Model</Label>
          <Select
            value={provider}
            onValueChange={(value) => setValue('llm_provider', value as 'ollama' | 'test')}
            disabled={createRun.isPending}
          >
            <SelectTrigger id="provider" className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ollama">Local (Ollama)</SelectItem>
              <SelectItem value="test">Deterministic (test)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button type="submit" disabled={createRun.isPending}>
          {createRun.isPending ? (
            <>
              <Loader2 className="animate-spin" /> Planning…
            </>
          ) : (
            <>
              <Send /> Start run
            </>
          )}
        </Button>
      </div>
      {createRun.isPending && (
        <p className="text-xs text-muted-foreground">
          This call blocks until the agent completes, fails, or needs your approval — a real
          local model can take a minute or more.
        </p>
      )}
    </form>
  )
}
