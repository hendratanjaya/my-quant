import { useCallback, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { dispatchChat, openStream } from './agent-api'
import { getUserIdFn, type ChatMessageRead } from './server-fns'

interface UIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  taskId?: string
  trace?: unknown[]
}

interface StreamEvent {
  type: 'start' | 'token' | 'tool_call' | 'tool_result' | 'handoff' | 'done' | 'error'
  data: Record<string, unknown>
}

export function useAgentChat() {
  const queryClient = useQueryClient()

  const [messages, setMessages] = useState<UIMessage[]>(() => {
    const cached = queryClient.getQueryData<ChatMessageRead[]>(['chat-history']) ?? []
    return cached.map((m) => ({
      id: `${m.id}`,
      role: m.role,
      content: m.content,
      taskId: m.task_id ?? undefined,
      trace: m.trace_json ? JSON.parse(m.trace_json) : undefined,
    }))
  })

  const [streamingText, setStreamingText] = useState<string>('')
  const [currentActivity, setCurrentActivity] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const traceRef = useRef<unknown[]>([])

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isRunning) return
    const userMsg: UIMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: text,
    }
    setMessages((prev) => [...prev, userMsg])
    setStreamingText('')
    setCurrentActivity(null)
    traceRef.current = []
    setIsRunning(true)

    try {
      const { task_id } = await dispatchChat(text)
      const { user_id } = await getUserIdFn()
      const es = openStream(task_id, user_id)
      let accumulated = ''
      es.onmessage = (ev) => {
        const evt = JSON.parse(ev.data) as StreamEvent
        switch (evt.type) {
          case 'token':
            accumulated += String(evt.data.text ?? '')
            setStreamingText(accumulated)
            break
          case 'tool_call':
            setCurrentActivity(`Calling ${String(evt.data.name)}…`)
            traceRef.current.push(evt.data)
            break
          case 'tool_result':
            traceRef.current.push(evt.data)
            break
          case 'handoff':
            setCurrentActivity(`Routing to ${String(evt.data.to)}…`)
            traceRef.current.push(evt.data)
            break
          case 'done':
            setMessages((prev) => [
              ...prev,
              {
                id: `local-${Date.now()}-a`,
                role: 'assistant',
                content: accumulated,
                taskId: task_id,
                trace: [...traceRef.current],
              },
            ])
            setStreamingText('')
            setCurrentActivity(null)
            setIsRunning(false)
            es.close()
            queryClient.invalidateQueries({ queryKey: ['chat-history'] })
            break
          case 'error':
            setCurrentActivity(`Error: ${String(evt.data.message)}`)
            setIsRunning(false)
            es.close()
            break
        }
      }
      es.onerror = () => {
        setIsRunning(false)
        es.close()
      }
    } catch (err) {
      setIsRunning(false)
      setCurrentActivity(`Error: ${(err as Error).message}`)
    }
  }, [isRunning])

  const clear = useCallback(() => {
    setMessages([])
    setStreamingText('')
    setCurrentActivity(null)
    queryClient.removeQueries({ queryKey: ['chat-history'] })
  }, [queryClient])

  return { messages, streamingText, currentActivity, isRunning, send, clear }
}
