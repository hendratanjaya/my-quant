import { create } from 'zustand'
import type { FundamentalReport } from '#/lib/api'

export type UserMessage = {
  id: string
  role: 'user'
  content: string
  ts: number
}

export type AssistantMessage =
  | { id: string; role: 'assistant'; kind: 'text'; content: string; ts: number }
  | { id: string; role: 'assistant'; kind: 'error'; content: string; ts: number }
  | { id: string; role: 'assistant'; kind: 'loading'; ts: number }
  | { id: string; role: 'assistant'; kind: 'fundamental'; report: FundamentalReport; ts: number }

export type ChatMessage = UserMessage | AssistantMessage

interface ChatState {
  messages: ChatMessage[]
  _userId: string | null
  hydrate: (userId: string) => void
  append: (message: ChatMessage) => void
  replace: (messageId: string, next: ChatMessage) => void
  clear: () => void
}

function storageKey(userId: string) {
  return `manual-chat:${userId}`
}

function save(userId: string | null, messages: ChatMessage[]) {
  if (!userId) return
  try {
    // never persist transient loading bubbles
    const durable = messages.filter(
      (m): m is UserMessage | Exclude<AssistantMessage, { kind: 'loading' }> =>
        !(m.role === 'assistant' && (m as AssistantMessage).kind === 'loading'),
    )
    localStorage.setItem(storageKey(userId), JSON.stringify(durable))
  } catch {
    // storage quota or SSR — ignore
  }
}

function load(userId: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(storageKey(userId))
    if (!raw) return []
    return JSON.parse(raw) as ChatMessage[]
  } catch {
    return []
  }
}

export const useChatStore = create<ChatState>()((set, get) => ({
  messages: [],
  _userId: null,

  hydrate: (userId) => {
    const messages = load(userId)
    set({ messages, _userId: userId })
  },

  append: (message) =>
    set((s) => {
      const messages = [...s.messages, message]
      save(s._userId, messages)
      return { messages }
    }),

  replace: (messageId, next) =>
    set((s) => {
      const messages = s.messages.map((m) => (m.id === messageId ? next : m))
      save(s._userId, messages)
      return { messages }
    }),

  clear: () =>
    set((s) => {
      save(s._userId, [])
      return { messages: [] }
    }),
}))

export function newMessageId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}
