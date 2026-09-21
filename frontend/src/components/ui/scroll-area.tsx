import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area'
import * as React from 'react'

import { cn } from '@/lib/utils'

function ScrollArea({
  className,
  children,
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.Root>) {
  return (
    <ScrollAreaPrimitive.Root className={cn('relative overflow-hidden', className)} {...props}>
      {/* Radix's viewport wraps children in a `display: table` div to measure content,
          which lets that content ignore the viewport's actual width (so flex/truncate
          children never wrap or clip correctly, only getting hard-clipped by this
          Root's overflow-hidden instead) -- forcing it back to `block` is the standard
          fix. */}
      <ScrollAreaPrimitive.Viewport className="size-full rounded-[inherit] [&>div]:block!">
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollAreaPrimitive.Scrollbar
        orientation="vertical"
        className="flex touch-none select-none p-0.5 transition-colors w-2.5 border-l border-l-transparent"
      >
        <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-border" />
      </ScrollAreaPrimitive.Scrollbar>
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

export { ScrollArea }
