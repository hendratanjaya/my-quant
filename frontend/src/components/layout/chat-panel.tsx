import { useEffect, useMemo, useRef, useState } from 'react'
import { Send } from 'lucide-react'

import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { FundamentalCard } from '#/components/chat/fundamental-card'
import { SlashMenu } from '#/components/chat/slash-menu'
import {
  filterCommands,
  findCommand,
  isSlashInput,
  parseSlashInput,
  type SlashCommand,
} from '#/lib/commands'
import {
  newMessageId,
  useChatStore,
  type AssistantMessage,
  type ChatMessage,
} from '#/lib/chat-store'
import { cn } from '#/lib/utils'

// Stable empty-array reference so `useChatStore((s) => s.sessions[key] ?? EMPTY)`
// doesn't return a new `[]` on every render — that would trigger an infinite
// re-render loop under Zustand's default Object.is equality check.
const EMPTY_MESSAGES: ChatMessage[] = []

interface ChatPanelProps {
  /** Session key — per-ticker (`bbri`) or `home` for the general chat on `/`. */
  sessionKey: string
  /** Human-readable label shown in the panel header. */
  contextLabel: string
}

export function ChatPanel({ sessionKey, contextLabel }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [slashIndex, setSlashIndex] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const messages = useChatStore((s) => s.sessions[sessionKey] ?? EMPTY_MESSAGES)
  const append = useChatStore((s) => s.append)
  const replace = useChatStore((s) => s.replace)

  const slashOpen = isSlashInput(input)
  const filtered = useMemo(
    () => (slashOpen ? filterCommands(input) : []),
    [input, slashOpen],
  )

  // Reset the highlighted slash-menu entry when the filter changes
  useEffect(() => {
    setSlashIndex(0)
  }, [input])

  // Autoscroll to the newest message
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length])

  async function send() {
    const raw = input.trim()
    if (!raw) return
    setInput('')

    const userMsg: ChatMessage = {
      id: newMessageId(),
      role: 'user',
      content: raw,
      ts: Date.now(),
    }
    append(sessionKey, userMsg)

    if (isSlashInput(raw)) {
      await dispatchSlash(raw)
    } else {
      // No agent backend yet — placeholder response.
      append(sessionKey, {
        id: newMessageId(),
        role: 'assistant',
        kind: 'text',
        ts: Date.now(),
        content:
          'Natural-language chat isn\'t wired to the agent yet. Try a slash command — type `/` to see options.',
      })
    }
  }

  async function dispatchSlash(raw: string) {
    const { command, args } = parseSlashInput(raw)
    const cmd = findCommand(command)
    if (!cmd) {
      append(sessionKey, {
        id: newMessageId(),
        role: 'assistant',
        kind: 'error',
        ts: Date.now(),
        content: `Unknown command: \`/${command}\`. Type \`/help\` for options.`,
      })
      return
    }

    const loadingId = newMessageId()
    append(sessionKey, {
      id: loadingId,
      role: 'assistant',
      kind: 'loading',
      ts: Date.now(),
    })

    const result = await cmd.run(args)
    const final: AssistantMessage =
      result.kind === 'fundamental'
        ? {
            id: loadingId,
            role: 'assistant',
            kind: 'fundamental',
            report: result.report,
            ts: Date.now(),
          }
        : result.kind === 'text'
          ? {
              id: loadingId,
              role: 'assistant',
              kind: 'text',
              content: result.content,
              ts: Date.now(),
            }
          : {
              id: loadingId,
              role: 'assistant',
              kind: 'error',
              content: result.content,
              ts: Date.now(),
            }
    replace(sessionKey, loadingId, final)
  }

  function pickCommand(cmd: SlashCommand) {
    setInput(`/${cmd.name} `)
    textareaRef.current?.focus()
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    const inMenu = slashOpen && filtered.length > 0
    if (inMenu && e.key === 'ArrowDown') {
      e.preventDefault()
      setSlashIndex((i) => (i + 1) % filtered.length)
      return
    }
    if (inMenu && e.key === 'ArrowUp') {
      e.preventDefault()
      setSlashIndex((i) => (i - 1 + filtered.length) % filtered.length)
      return
    }
    if (inMenu && e.key === 'Tab') {
      e.preventDefault()
      pickCommand(filtered[slashIndex])
      return
    }
    // Enter on a bare command name (no args yet) autocompletes; otherwise sends.
    const noArgsYet = !input.includes(' ')
    if (inMenu && e.key === 'Enter' && !e.shiftKey && noArgsYet) {
      e.preventDefault()
      pickCommand(filtered[slashIndex])
      return
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-b px-4 py-3">
        <h2 className="text-sm font-medium text-muted-foreground">
          Agent session
        </h2>
        <p className="text-lg font-semibold">{contextLabel}</p>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-3"
      >
        {messages.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            Session <code className="rounded bg-muted px-1">{sessionKey}</code>{' '}
            — no messages yet. Try <code>/fd BBRI</code> or type{' '}
            <code>/</code> to see options.
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      <div className="relative border-t p-3">
        {slashOpen && (
          <SlashMenu
            commands={filtered}
            activeIndex={slashIndex}
            onSelect={pickCommand}
            onHoverIndex={setSlashIndex}
          />
        )}
        <form
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void send()
          }}
        >
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask something, or use a slash command…"
            rows={2}
            className="resize-none"
          />
          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={!input.trim()}>
              <Send className="mr-1 h-3 w-3" />
              Send
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Message rendering ───────────────────────────────────────────────

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    )
  }

  if (message.kind === 'loading') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground" />
        Thinking…
      </div>
    )
  }

  if (message.kind === 'fundamental') {
    return <FundamentalCard report={message.report} />
  }

  return (
    <div
      className={cn(
        'max-w-[95%] rounded-lg px-3 py-2 text-sm',
        message.kind === 'error'
          ? 'bg-red-500/10 text-red-500'
          : 'bg-white/5 text-foreground',
      )}
    >
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  )
}
