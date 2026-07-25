import { getUserIdFn } from './server-fns'

const BASE = import.meta.env.VITE_BACKEND_URL as string

async function headers(): Promise<HeadersInit> {
  const { user_id } = await getUserIdFn()
  return { 'X-User-Id': user_id, 'Content-Type': 'application/json' }
}

export async function dispatchChat(message: string): Promise<{ task_id: string }> {
  const res = await fetch(`${BASE}/api/agent/chat`, {
    method: 'POST',
    headers: await headers(),
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`dispatch failed: ${res.status}`)
  return res.json()
}

export function openStream(taskId: string, userId: string): EventSource {
  return new EventSource(
    `${BASE}/api/agent/stream/${taskId}?user_id=${encodeURIComponent(userId)}`,
  )
}

export async function dispatchScreen(signals: string[]): Promise<{ task_id: string }> {
  const res = await fetch(`${BASE}/api/screen`, {
    method: 'POST',
    headers: await headers(),
    body: JSON.stringify({ signals }),
  })
  if (!res.ok) throw new Error(`screen dispatch failed: ${res.status}`)
  return res.json()
}

export function openScreenStream(taskId: string, userId: string): EventSource {
  return new EventSource(
    `${BASE}/api/screen/stream/${taskId}?user_id=${encodeURIComponent(userId)}`,
  )
}

