import type { Candle } from '#/lib/mock-ohlcv'
import type { SeededSummary } from '#/lib/server-fns'

const API_BASE = import.meta.env.BACKEND_URL

export async function fetchOhlcv(
  symbol: string,
  days = 730,
  interval = '1d',
): Promise<Candle[]> {
  const res = await fetch(
    `${API_BASE}/api/ohlcv/${symbol}?days=${days}&interval=${interval}`,
  )
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<Candle[]>
}

/** No auth required — reads the local archive metadata. */
export async function listSeeded(): Promise<SeededSummary[]> {
  const res = await fetch(`${API_BASE}/api/seed`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export type { SeededSummary }

// ── Fundamental report ──────────────────────────────────────────────

export type MetricCategory = 'valuation' | 'quality' | 'growth' | 'ttm'

export interface MetricPercentile {
  metric: string
  category: MetricCategory
  current: number
  percentile: number
  min_value: number
  max_value: number
}

export interface QuarterPoint {
  period_end: string // ISO date
  value: number
}

export interface QuarterlySeries {
  metric: string
  points: QuarterPoint[]
}

export interface PeriodValues {
  period_end: string // ISO date
  values: Record<string, number | null>
}

export interface FundamentalReport {
  symbol: string
  name: string
  as_of: string // ISO date
  metrics: MetricPercentile[]
  quarterly: QuarterlySeries[]
  time_series: PeriodValues[]
  comparison: PeriodValues[]
  reading: string
}

export async function fetchFundamental(symbol: string): Promise<FundamentalReport> {
  const res = await fetch(
    `${API_BASE}/api/fundamental/${symbol.toUpperCase()}`,
  )
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<FundamentalReport>
}
