import {
  Bot,
  FolderOpen,
  Globe,
  LayoutDashboard,
  ListChecks,
  Settings,
  ShieldCheck,
  SquareStack,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
}

export const navItems: NavItem[] = [
  { label: 'Overview', path: '/', icon: LayoutDashboard },
  { label: 'Agent', path: '/agent', icon: Bot },
  { label: 'Tasks', path: '/tasks', icon: ListChecks },
  { label: 'Approvals', path: '/approvals', icon: ShieldCheck },
  { label: 'Browser', path: '/browser', icon: Globe },
  { label: 'Workspace', path: '/workspace', icon: FolderOpen },
  { label: 'Memory', path: '/memory', icon: SquareStack },
  { label: 'Settings', path: '/settings', icon: Settings },
]
