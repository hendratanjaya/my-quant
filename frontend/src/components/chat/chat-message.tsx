import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  role: 'user' | 'assistant'
  content: string
  trace?: unknown[]
  streaming?: boolean
}

export function ChatMessage({ role, content, trace, streaming = false }: Props) {
  const [open, setOpen] = useState(false)
  const isAssistant = role === 'assistant'
  return (
    <div className={`px-3 py-2 text-sm ${isAssistant ? 'bg-muted/30' : ''}`}>
      <div className="text-xs uppercase text-muted-foreground mb-1">{role}</div>
      {isAssistant && !streaming ? (
        <div className="prose prose-sm dark:prose-invert max-w-none
          [&>*:first-child]:mt-0 [&>*:last-child]:mb-0
          prose-p:my-1 prose-headings:my-2 prose-headings:font-semibold
          prose-h1:text-base prose-h2:text-sm prose-h3:text-sm
          prose-ul:my-1 prose-ol:my-1 prose-li:my-0
          prose-table:text-xs prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1
          prose-pre:bg-background/70 prose-pre:text-xs
          prose-code:text-xs prose-code:bg-background/70 prose-code:px-1 prose-code:rounded
          prose-strong:font-semibold prose-hr:my-2">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : (
        <div className="whitespace-pre-wrap">{content}</div>
      )}
      {isAssistant && trace && trace.length > 0 && (
        <div className="mt-2">
          <button
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? '▾' : '▸'} reasoning trace ({trace.length})
          </button>
          {open && (
            <pre className="text-xs mt-1 bg-background/50 p-2 rounded overflow-x-auto">
              {JSON.stringify(trace, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
