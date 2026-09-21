import { ChevronRight, File, Folder, FolderOpen, Home } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { FilePreview } from '@/features/workspace/components/file-preview'
import { useWorkspaceEntries } from '@/features/workspace/use-workspace'
import { getErrorMessage } from '@/lib/api-client'
import { formatBytes, formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

export function WorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const path = searchParams.get('path') ?? ''
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  const { data: listing, isLoading, isError, error } = useWorkspaceEntries(path)

  function navigateTo(nextPath: string) {
    setSelectedFile(null)
    if (nextPath) {
      setSearchParams({ path: nextPath })
    } else {
      setSearchParams({})
    }
  }

  const segments = listing && listing.path !== '.' ? listing.path.split('/') : []

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Files and folders the agent creates and organizes.</CardDescription>
          <div className="flex flex-wrap items-center gap-1 pt-1 text-xs text-muted-foreground">
            <button
              type="button"
              onClick={() => navigateTo('')}
              className="flex items-center gap-1 hover:text-foreground"
            >
              <Home className="size-3" /> root
            </button>
            {segments.map((segment, index) => (
              <span key={index} className="flex items-center gap-1">
                <ChevronRight className="size-3" />
                <button
                  type="button"
                  onClick={() => navigateTo(segments.slice(0, index + 1).join('/'))}
                  className="hover:text-foreground"
                >
                  {segment}
                </button>
              </span>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : isError ? (
            <ErrorState
              description={getErrorMessage(error, "Couldn't load this folder.")}
            />
          ) : !listing || listing.entries.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="This folder is empty"
              description="Files the agent creates here will show up automatically."
            />
          ) : (
            <ul className="space-y-0.5">
              {listing.entries.map((entry) => (
                <li key={entry.path}>
                  <button
                    type="button"
                    onClick={() =>
                      entry.is_dir ? navigateTo(entry.path) : setSelectedFile(entry.path)
                    }
                    className={cn(
                      'flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors',
                      selectedFile === entry.path
                        ? 'bg-accent text-accent-foreground'
                        : 'hover:bg-accent/60',
                    )}
                  >
                    {entry.is_dir ? (
                      <Folder className="size-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <File className="size-4 shrink-0 text-muted-foreground" />
                    )}
                    <span className="min-w-0 flex-1 truncate">{entry.name}</span>
                    {!entry.is_dir && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatBytes(entry.size_bytes)}
                      </span>
                    )}
                    <span className="w-16 shrink-0 text-right text-xs text-muted-foreground">
                      {formatRelativeTime(entry.modified_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          {selectedFile && <CardDescription className="font-mono">{selectedFile}</CardDescription>}
        </CardHeader>
        <Separator />
        <CardContent className="pt-5">
          {selectedFile ? (
            <FilePreview path={selectedFile} />
          ) : (
            <EmptyState
              icon={File}
              title="No file selected"
              description="Choose a file from the list to preview its contents here."
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
