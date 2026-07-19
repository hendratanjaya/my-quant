import type { Candle } from '#/lib/mock-ohlcv'

const API_BASE = import.meta.env.BACKEND_URL

export async function fetchOhlcv(symbol: string, days = 730, interval = '1d'): Promise<Candle[]> {
  const res = await fetch(`${API_BASE}/api/ohlcv/${symbol}?days=${days}&interval=${interval}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<Candle[]>
}
