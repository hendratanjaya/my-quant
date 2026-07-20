import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
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
  | {
      id: string
      role: 'assistant'
      kind: 'fundamental'
      report: FundamentalReport
      ts: number
    }

export type ChatMessage = UserMessage | AssistantMessage

interface ChatState {
  /** Messages keyed by session (`home`, `bbri`, `bbca`, …). */
  sessions: Record<string, ChatMessage[]>
  append: (sessionKey: string, message: ChatMessage) => void
  replace: (
    sessionKey: string,
    messageId: string,
    next: ChatMessage,
  ) => void
  clear: (sessionKey: string) => void
}

const STORAGE_KEY = 'chat-sessions'

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessions: {},
      append: (sessionKey, message) =>
        set((s) => ({
          sessions: {
            ...s.sessions,
            [sessionKey]: [...(s.sessions[sessionKey] ?? []), message],
          },
        })),
      replace: (sessionKey, messageId, next) =>
        set((s) => ({
          sessions: {
            ...s.sessions,
            [sessionKey]: (s.sessions[sessionKey] ?? []).map((m) =>
              m.id === messageId ? next : m,
            ),
          },
        })),
      clear: (sessionKey) =>
        set((s) => ({
          sessions: { ...s.sessions, [sessionKey]: [] },
        })),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
    },
  ),
)

export function newMessageId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}
