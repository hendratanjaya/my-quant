import { useEffect, useRef, useState } from 'react'
import { Switch } from '#/components/ui/switch'
import { ChatPanel } from '#/components/layout/chat-panel'
import { ActivityIndicator } from './activity-indicator'
import { ChatMessage } from './chat-message'
import { useAgentChat } from '#/lib/use-agent-chat'
import { clearChatHistoryFn } from '#/lib/server-fns'
import { useChatStore } from '#/lib/chat-store'

export function ChatDrawer() {
  const { messages, streamingText, currentActivity, isRunning, send, clear: clearAgent } = useAgentChat()
  const [draft, setDraft] = useState('')
  const [agentMode, setAgentMode] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)
  const clearStore = useChatStore((s) => s.clear)

  async function handleClear() {
    if (agentMode) {
      await clearChatHistoryFn()
      clearAgent()
    } else {
      clearStore()
    }
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages, streamingText])

  return (
    <div className="flex flex-col h-full overflow-hidden border-l border-border">
      <div className="px-4 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">Chat</span>
          <button
            onClick={handleClear}
            className="text-xs text-muted-foreground hover:text-destructive transition-colors"
            title="Clear all messages"
          >
            clear
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${agentMode ? 'text-muted-foreground' : 'text-foreground'}`}>
            Manual
          </span>
          <Switch
            size="sm"
            checked={agentMode}
            onCheckedChange={setAgentMode}
          />
          <span className={`text-xs font-medium ${agentMode ? 'text-foreground' : 'text-muted-foreground'}`}>
            Agent
          </span>
        </div>
      </div>

      {agentMode ? (
        <>
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            {messages.map((m) => (
              <ChatMessage key={m.id} role={m.role} content={m.content} trace={m.trace as unknown[]} />
            ))}
            {streamingText && (
              <ChatMessage role="assistant" content={streamingText} streaming />
            )}
            <ActivityIndicator text={currentActivity} />
          </div>
          <form
            className="border-t border-border p-3 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (draft.trim()) {
                send(draft)
                setDraft('')
              }
            }}
          >
            <input
              className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={isRunning ? 'thinking…' : 'ask about an IDX ticker'}
              disabled={isRunning}
            />
            <button
              type="submit"
              className="px-3 py-2 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
              disabled={isRunning || !draft.trim()}
            >
              send
            </button>
          </form>
        </>
      ) : (
        <div className="flex-1 min-h-0 overflow-hidden">
          <ChatPanel />
        </div>
      )}
    </div>
  )
}
