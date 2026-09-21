import { Pencil, SquareStack, Trash2 } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorState } from '@/components/layout/error-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { PreferenceFormDialog } from '@/features/preferences/components/preference-form-dialog'
import { useDeletePreference, usePreferences } from '@/features/preferences/use-preferences'
import { formatDateTime } from '@/lib/format'

export function MemoryPage() {
  const { data: preferences, isLoading, isError } = usePreferences()
  const deletePreference = useDeletePreference()

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4 space-y-0">
        <div>
          <CardTitle>Memory</CardTitle>
          <CardDescription>Preferences the agent may use to inform future runs.</CardDescription>
        </div>
        <PreferenceFormDialog />
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading preferences…</p>
        ) : isError ? (
          <ErrorState description="Couldn't reach the backend to load preferences. Try again shortly." />
        ) : !preferences || preferences.length === 0 ? (
          <EmptyState
            icon={SquareStack}
            title="No preferences saved"
            description="Preferences are only stored here after you explicitly confirm them — nothing is inferred automatically from conversations."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {preferences.map((preference) => (
                <TableRow key={preference.id}>
                  <TableCell className="font-mono text-xs">
                    {preference.key}
                    {preference.description && (
                      <p className="mt-0.5 font-sans text-xs text-muted-foreground">
                        {preference.description}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="max-w-xs truncate font-mono text-xs">
                    {JSON.stringify(preference.value)}
                  </TableCell>
                  <TableCell className="space-x-1">
                    <Badge variant={preference.confirmed_by_user ? 'success' : 'outline'}>
                      {preference.confirmed_by_user ? 'Confirmed' : 'Proposed'}
                    </Badge>
                    {!preference.available_to_future_runs && (
                      <Badge variant="outline">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTime(preference.updated_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <PreferenceFormDialog
                        preference={preference}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label="Edit preference">
                            <Pencil />
                          </Button>
                        }
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Delete preference"
                        disabled={deletePreference.isPending}
                        onClick={() => deletePreference.mutate(preference.id)}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
