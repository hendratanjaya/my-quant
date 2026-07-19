import { Button } from '#/components/ui/button'
import { ScrollArea } from '#/components/ui/scroll-area'
import { Textarea } from '#/components/ui/textarea'

interface ChatPanelProps {
  /** Session key — per-ticker (`bbri`) or `home` for the general chat on `/`. */
  sessionKey: string
  /** Human-readable label shown in the panel header. */
  contextLabel: string
}

export function ChatPanel({ sessionKey, contextLabel }: ChatPanelProps) {
  return (
    <div className="flex h-full flex-col">
      <header className="border-b px-4 py-3">
        <h2 className="text-sm font-medium text-muted-foreground">
          Agent session
        </h2>
        <p className="text-lg font-semibold">{contextLabel}</p>
      </header>

      <ScrollArea className="flex-1 px-4 py-3">
        <div className="text-sm text-muted-foreground">
          Session <code className="rounded bg-muted px-1">{sessionKey}</code>{' '}
          — no messages yet. Try <code>/fd</code>, <code>/screen</code>, or ask
          in natural language.
        </div>
      </ScrollArea>

      <div className="border-t p-3">
        <form className="flex flex-col gap-2">
          <Textarea
            placeholder="Ask something, or use a slash command…"
            rows={2}
            className="resize-none"
          />
          <div className="flex justify-end">
            <Button type="submit" size="sm">
              Send
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
