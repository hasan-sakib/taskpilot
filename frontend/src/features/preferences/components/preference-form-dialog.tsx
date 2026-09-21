import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import type { PreferenceResponse } from '@/features/preferences/api'
import { useCreatePreference, useUpdatePreference } from '@/features/preferences/use-preferences'

const preferenceFormSchema = z.object({
  key: z.string().min(1, 'Required').max(200),
  valueJson: z.string().min(1, 'Required').refine(
    (value) => {
      try {
        JSON.parse(value)
        return true
      } catch {
        return false
      }
    },
    { message: 'Must be valid JSON, e.g. true, "some text", 42, or {"a": 1}' },
  ),
  description: z.string().optional(),
  confirmed_by_user: z.boolean(),
  available_to_future_runs: z.boolean(),
})

type PreferenceFormValues = z.infer<typeof preferenceFormSchema>

interface PreferenceFormDialogProps {
  preference?: PreferenceResponse
  trigger?: React.ReactNode
}

export function PreferenceFormDialog({ preference, trigger }: PreferenceFormDialogProps) {
  const [open, setOpen] = useState(false)
  const isEditing = !!preference
  const createPreference = useCreatePreference()
  const updatePreference = useUpdatePreference()
  const isPending = createPreference.isPending || updatePreference.isPending

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<PreferenceFormValues>({
    resolver: zodResolver(preferenceFormSchema),
    defaultValues: {
      key: preference?.key ?? '',
      valueJson: preference ? JSON.stringify(preference.value) : '',
      description: preference?.description ?? '',
      confirmed_by_user: preference?.confirmed_by_user ?? true,
      available_to_future_runs: preference?.available_to_future_runs ?? true,
    },
  })

  useEffect(() => {
    if (open) {
      reset({
        key: preference?.key ?? '',
        valueJson: preference ? JSON.stringify(preference.value) : '',
        description: preference?.description ?? '',
        confirmed_by_user: preference?.confirmed_by_user ?? true,
        available_to_future_runs: preference?.available_to_future_runs ?? true,
      })
    }
  }, [open, preference, reset])

  const confirmedByUser = watch('confirmed_by_user')
  const availableToFutureRuns = watch('available_to_future_runs')

  const onSubmit = handleSubmit(async (values) => {
    const body = {
      value: JSON.parse(values.valueJson) as unknown,
      description: values.description || null,
      confirmed_by_user: values.confirmed_by_user,
      available_to_future_runs: values.available_to_future_runs,
    }
    try {
      if (isEditing) {
        await updatePreference.mutateAsync({ id: preference.id, body })
      } else {
        await createPreference.mutateAsync({ key: values.key, ...body })
      }
      setOpen(false)
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button size="sm">
            <Plus /> New preference
          </Button>
        )}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit preference' : 'New preference'}</DialogTitle>
          <DialogDescription>
            Only preferences you explicitly confirm here are ever used to influence future
            runs — nothing is inferred automatically.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="key">Key</Label>
            <Input
              id="key"
              placeholder="tool.python.execute.require_approval"
              disabled={isEditing}
              {...register('key')}
            />
            {errors.key && <p className="text-xs text-destructive">{errors.key.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="valueJson">Value (JSON)</Label>
            <Textarea id="valueJson" rows={3} placeholder="true" {...register('valueJson')} />
            {errors.valueJson && (
              <p className="text-xs text-destructive">{errors.valueJson.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description (optional)</Label>
            <Input id="description" {...register('description')} />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="confirmed" className="font-normal text-muted-foreground">
              Confirmed — available for the agent to use
            </Label>
            <Switch
              id="confirmed"
              checked={confirmedByUser}
              onCheckedChange={(checked) => setValue('confirmed_by_user', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="available" className="font-normal text-muted-foreground">
              Apply to future runs
            </Label>
            <Switch
              id="available"
              checked={availableToFutureRuns}
              onCheckedChange={(checked) => setValue('available_to_future_runs', checked)}
            />
          </div>

          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isEditing ? 'Save changes' : 'Create preference'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
