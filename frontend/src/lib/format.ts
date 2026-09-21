export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(`${value}Z`).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(`${value}Z`)
  const diffMs = date.getTime() - Date.now()
  const diffSeconds = Math.round(diffMs / 1000)
  const absSeconds = Math.abs(diffSeconds)

  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
    ['second', 1],
  ]

  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  for (const [unit, secondsInUnit] of units) {
    if (absSeconds >= secondsInUnit || unit === 'second') {
      const value = Math.round(diffSeconds / secondsInUnit)
      return formatter.format(value, unit)
    }
  }
  return formatter.format(0, 'second')
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** exponent
  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`
}
