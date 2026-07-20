import { useEffect, useRef } from 'react'
import { cn } from '#/lib/utils'
import type { SlashCommand } from '#/lib/commands'

interface SlashMenuProps {
  commands: SlashCommand[]
  activeIndex: number
  onSelect: (cmd: SlashCommand) => void
  onHoverIndex: (i: number) => void
}

/**
 * Anchored above the chat input. Rendered only when the input starts with `/`
 * and there's at least one matching command.
 */
export function SlashMenu({
  commands,
  activeIndex,
  onSelect,
  onHoverIndex,
}: SlashMenuProps) {
  const activeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  if (commands.length === 0) return null

  return (
    <div className="absolute inset-x-0 bottom-full mb-1 max-h-64 overflow-y-auto rounded-md border border-white/10 bg-popover shadow-md">
      {commands.map((cmd, i) => (
        <button
          key={cmd.name}
          ref={i === activeIndex ? activeRef : null}
          type="button"
          className={cn(
            'flex w-full items-baseline gap-3 px-3 py-2 text-left transition-colors',
            i === activeIndex ? 'bg-accent' : 'hover:bg-accent/60',
          )}
          onMouseEnter={() => onHoverIndex(i)}
          onMouseDown={(e) => {
            e.preventDefault()
            onSelect(cmd)
          }}
        >
          <span className="w-24 shrink-0 font-mono text-xs font-semibold">
            {cmd.usage}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            {cmd.description}
          </span>
        </button>
      ))}
    </div>
  )
}
