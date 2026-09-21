import { AlertTriangle } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  description: string
}

export function ErrorState({ title = 'Could not load this', description }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-destructive/40 py-16 text-center">
      <div className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="size-5" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-destructive">{title}</p>
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
