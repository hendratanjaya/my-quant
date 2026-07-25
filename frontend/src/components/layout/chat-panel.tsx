import { useEffect, useMemo, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Link } from '@tanstack/react-router'

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
import { getUserIdFn } from '#/lib/server-fns'
import { cn } from '#/lib/utils'

export function ChatPanel() {
  const [input, setInput] = useState('')
  const [slashIndex, setSlashIndex] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const messages = useChatStore((s) => s.messages)
  const append = useChatStore((s) => s.append)
  const replace = useChatStore((s) => s.replace)
  const hydrate = useChatStore((s) => s.hydrate)

  useEffect(() => {
    getUserIdFn().then(({ user_id }) => hydrate(user_id))
  }, [])

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
    append(userMsg)

    if (isSlashInput(raw)) {
      await dispatchSlash(raw)
    } else {
      append({
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
      append({
        id: newMessageId(),
        role: 'assistant',
        kind: 'error',
        ts: Date.now(),
        content: `Unknown command: \`/${command}\`. Type \`/help\` for options.`,
      })
      return
    }

    const loadingId = newMessageId()
    append({
      id: loadingId,
      role: 'assistant',
      kind: 'loading',
      ts: Date.now(),
    })

    const result = await cmd.run(args, (progressContent) => {
      replace(loadingId, {
        id: loadingId, role: 'assistant', kind: 'text',
        content: progressContent, ts: Date.now(),
      })
    })
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
    replace(loadingId, final)
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
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-3"
      >
        {messages.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            No messages yet. Try <code>/fd BBRI</code> or type{' '}
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
      {message.kind === 'error' ? (
        <p className="whitespace-pre-wrap">{message.content}</p>
      ) : (
        <div className="prose prose-sm dark:prose-invert max-w-none
          [&>*:first-child]:mt-0 [&>*:last-child]:mb-0
          prose-p:my-1 prose-headings:my-2 prose-headings:font-semibold
          prose-h1:text-base prose-h2:text-sm prose-h3:text-sm
          prose-ul:my-1 prose-ol:my-1 prose-li:my-0
          prose-strong:font-semibold prose-hr:my-2">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) =>
                href?.startsWith('/') ? (
                  <Link to={href} className="font-semibold underline underline-offset-2 hover:opacity-80">
                    {children}
                  </Link>
                ) : (
                  <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:opacity-80">
                    {children}
                  </a>
                ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  )
}
