/**
 * Server functions for auth + proxy calls to the Python backend.
 *
 * The JWT lives inside an httpOnly, encrypted, signed session cookie managed by
 * @tanstack/react-start/server. Client code cannot read it. Any call that
 * needs the JWT goes through these server functions — the server reads the
 * session, then forwards the request to the Python API.
 */

import { createServerFn } from '@tanstack/react-start'
import { getOrCreateUserId } from '#/lib/server-identity'
import { serverSession } from '#/lib/server-session'

const API_BASE = process.env.BACKEND_URL

// ── Discriminated results — keeps client type-safe without relying on error
//    class survival through the RPC serialization boundary.

export type SeedResult =
  | { ok: true; data: SeededSummary }
  | { ok: false; error: 'unauthorized' }
  | { ok: false; error: 'already-seeded' }
  | { ok: false; error: 'upstream'; status: number }

export interface SeededSummary {
  symbol: string
  seeded_at: string
  row_count: number
  period_first: string | null
  period_last: string | null
}

// ── Identity ────────────────────────────────────────────────────────
// Lazy-initialized on first call. Safe to call anywhere on the server;
// the httpOnly `user-identity` cookie gets set on the response if missing.

export const getUserIdFn = createServerFn({ method: 'GET' }).handler(
  async (): Promise<{ user_id: string }> => ({
    user_id: await getOrCreateUserId(),
  }),
)

// ── Auth state ──────────────────────────────────────────────────────

export const hasTokenFn = createServerFn({ method: 'GET' }).handler(
  async (): Promise<{ hasToken: boolean }> => {
    const session = await serverSession()
    return { hasToken: Boolean(session.data.token) }
  },
)

export const saveTokenFn = createServerFn({ method: 'POST' })
  .validator((token: unknown): string => {
    if (typeof token !== 'string') throw new Error('token must be a string')
    const trimmed = token.trim()
    if (!trimmed) throw new Error('token cannot be empty')
    return trimmed
  })
  .handler(async ({ data: token }) => {
    const session = await serverSession()
    await session.update({ token })
    return { ok: true as const }
  })

export const clearTokenFn = createServerFn({ method: 'POST' }).handler(
  async () => {
    const session = await serverSession()
    await session.clear()
    return { ok: true as const }
  },
)

// ── Seed proxy ──────────────────────────────────────────────────────

export const seedTickerFn = createServerFn({ method: 'POST' })
  .validator((symbol: unknown): string => {
    if (typeof symbol !== 'string') throw new Error('symbol must be a string')
    const trimmed = symbol.trim().toUpperCase()
    if (!trimmed) throw new Error('symbol cannot be empty')
    return trimmed
  })
  .handler(async ({ data: symbol }): Promise<SeedResult> => {
    const session = await serverSession()
    const token = session.data.token
    if (!token) return { ok: false, error: 'unauthorized' }

    const res = await fetch(`${API_BASE}/api/seed/${symbol}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })

    if (res.status === 401) {
      await session.clear()
      return { ok: false, error: 'unauthorized' }
    }
    if (res.status === 409) return { ok: false, error: 'already-seeded' }
    if (!res.ok) return { ok: false, error: 'upstream', status: res.status }

    const data = (await res.json()) as SeededSummary
    return { ok: true, data }
  })
