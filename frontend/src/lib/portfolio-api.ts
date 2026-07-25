import { getUserIdFn } from './server-fns'

export interface Position {
  ticker: string
  lots: number
  avgPrice: number
}

interface ServerPosition {
  ticker: string
  lots: number
  avg_price: number
  created_at: string
  updated_at: string
}

const BASE = import.meta.env.VITE_API_BASE_URL as string

async function withUserId(): Promise<HeadersInit> {
  const { user_id } = await getUserIdFn()
  return { 'X-User-Id': user_id, 'Content-Type': 'application/json' }
}

function fromServer(p: ServerPosition): Position {
  return { ticker: p.ticker, lots: p.lots, avgPrice: p.avg_price }
}

export async function fetchPortfolio(): Promise<Position[]> {
  const res = await fetch(`${BASE}/api/portfolio`, { headers: await withUserId() })
  if (!res.ok) throw new Error(`portfolio list failed: ${res.status}`)
  return ((await res.json()) as ServerPosition[]).map(fromServer)
}

export async function addPortfolio(p: Position): Promise<Position> {
  const res = await fetch(`${BASE}/api/portfolio`, {
    method: 'POST',
    headers: await withUserId(),
    body: JSON.stringify({ ticker: p.ticker, lots: p.lots, avg_price: p.avgPrice }),
  })
  if (!res.ok) throw new Error(`portfolio add failed: ${res.status}`)
  return fromServer(await res.json())
}

export async function patchPortfolio(
  ticker: string,
  patch: Partial<Omit<Position, 'ticker'>>,
): Promise<Position> {
  const body: Record<string, number> = {}
  if (patch.lots !== undefined) body.lots = patch.lots
  if (patch.avgPrice !== undefined) body.avg_price = patch.avgPrice
  const res = await fetch(`${BASE}/api/portfolio/${ticker}`, {
    method: 'PATCH',
    headers: await withUserId(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`portfolio patch failed: ${res.status}`)
  return fromServer(await res.json())
}

export async function deletePortfolio(ticker: string): Promise<void> {
  const res = await fetch(`${BASE}/api/portfolio/${ticker}`, {
    method: 'DELETE',
    headers: await withUserId(),
  })
  if (!res.ok && res.status !== 204) throw new Error(`portfolio delete failed: ${res.status}`)
}
