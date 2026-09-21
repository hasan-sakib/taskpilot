import type { badgeVariants } from '@/components/ui/badge'
import type { VariantProps } from 'class-variance-authority'

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>['variant']>

const RUN_STATUS_VARIANTS: Record<string, BadgeVariant> = {
  pending: 'secondary',
  running: 'warning',
  paused_for_approval: 'warning',
  completed: 'success',
  failed: 'destructive',
  cancelled: 'outline',
}

const TASK_STATUS_VARIANTS: Record<string, BadgeVariant> = {
  pending: 'secondary',
  ready: 'secondary',
  in_progress: 'warning',
  blocked_on_approval: 'warning',
  completed: 'success',
  failed: 'destructive',
  skipped: 'outline',
  cancelled: 'outline',
}

const APPROVAL_STATUS_VARIANTS: Record<string, BadgeVariant> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'destructive',
  expired: 'outline',
  invalidated: 'outline',
}

const BROWSER_SESSION_STATUS_VARIANTS: Record<string, BadgeVariant> = {
  active: 'success',
  closed: 'outline',
  crashed: 'destructive',
}

function variantFor(map: Record<string, BadgeVariant>, status: string): BadgeVariant {
  return map[status] ?? 'secondary'
}

export function runStatusVariant(status: string): BadgeVariant {
  return variantFor(RUN_STATUS_VARIANTS, status)
}

export function taskStatusVariant(status: string): BadgeVariant {
  return variantFor(TASK_STATUS_VARIANTS, status)
}

export function approvalStatusVariant(status: string): BadgeVariant {
  return variantFor(APPROVAL_STATUS_VARIANTS, status)
}

export function browserSessionStatusVariant(status: string): BadgeVariant {
  return variantFor(BROWSER_SESSION_STATUS_VARIANTS, status)
}

export function formatStatusLabel(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function isTerminalRunStatus(status: string): boolean {
  return status === 'completed' || status === 'failed' || status === 'cancelled'
}
