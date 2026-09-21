import { Download, FileText } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { Button } from '@/components/ui/button'
import { classifyFile } from '@/features/workspace/file-kind'
import { workspaceFileUrl } from '@/features/workspace/api'
import { useWorkspaceFileText } from '@/features/workspace/use-workspace'

interface FilePreviewProps {
  path: string
}

export function FilePreview({ path }: FilePreviewProps) {
  const kind = classifyFile(path)
  const name = path.split('/').pop() ?? path

  if (kind === 'image') {
    return (
      <div className="space-y-2">
        <img
          src={workspaceFileUrl(path)}
          alt={name}
          className="max-h-96 rounded-md border border-border object-contain"
        />
        <DownloadLink path={path} />
      </div>
    )
  }

  if (kind === 'text') {
    return <TextPreview path={path} />
  }

  return (
    <EmptyState
      icon={FileText}
      title="No preview available"
      description={`${name} isn't a previewable text or image file.`}
    />
  )
}

function TextPreview({ path }: { path: string }) {
  const { data, isLoading, isError } = useWorkspaceFileText(path)

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading preview…</p>
  }
  if (isError) {
    return <p className="text-sm text-destructive">Could not load this file.</p>
  }

  return (
    <div className="space-y-2">
      <pre className="max-h-96 overflow-auto rounded-md border border-border bg-muted p-3 text-xs">
        {data}
      </pre>
      <DownloadLink path={path} />
    </div>
  )
}

function DownloadLink({ path }: { path: string }) {
  return (
    <Button variant="outline" size="sm" asChild>
      <a href={workspaceFileUrl(path)} download>
        <Download /> Download
      </a>
    </Button>
  )
}
