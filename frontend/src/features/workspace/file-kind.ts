const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'])
const TEXT_EXTENSIONS = new Set([
  'txt',
  'md',
  'json',
  'py',
  'js',
  'ts',
  'tsx',
  'jsx',
  'csv',
  'log',
  'yaml',
  'yml',
  'html',
  'css',
  'sh',
])

export type FileKind = 'image' | 'text' | 'other'

export function classifyFile(name: string): FileKind {
  const extension = name.split('.').pop()?.toLowerCase() ?? ''
  if (IMAGE_EXTENSIONS.has(extension)) return 'image'
  if (TEXT_EXTENSIONS.has(extension)) return 'text'
  return 'other'
}
