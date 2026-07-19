export type Timeframe = 'D' | 'W' | 'M'

export const TIMEFRAME_DAYS: Record<Timeframe, number> = {
  D: 730,
  W: 1825,
  M: 3650,
}

export const TIMEFRAME_INTERVAL: Record<Timeframe, string> = {
  D: '1d',
  W: '1wk',
  M: '1mo',
}

export function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = []
  let sum = 0
  for (let i = 0; i < values.length; i++) {
    sum += values[i]
    if (i >= period) sum -= values[i - period]
    out.push(i >= period - 1 ? sum / period : null)
  }
  return out
}

export function macd(
  closes: number[],
  fast = 12,
  slow = 26,
  signalPeriod = 9,
): {
  macd: (number | null)[]
  signal: (number | null)[]
  histogram: (number | null)[]
} {
  const smaFast = sma(closes, fast)
  const smaSlow = sma(closes, slow)
  const macdLine = closes.map((_, i) => {
    const f = smaFast[i]
    const s = smaSlow[i]
    return f !== null && s !== null ? f - s : null
  })
  const firstValid = macdLine.findIndex((v) => v !== null)
  const rawSignal = sma(macdLine.slice(firstValid) as number[], signalPeriod)
  const signal = macdLine.map((v, i) =>
    v === null ? null : rawSignal[i - firstValid] ?? null,
  )
  const histogram = macdLine.map((v, i) => {
    const s = signal[i]
    return v !== null && s !== null ? v - s : null
  })
  return { macd: macdLine, signal, histogram }
}

export function stochastic(
  highs: number[],
  lows: number[],
  closes: number[],
  kLength = 5,
  kSmoothing = 3,
  dSmoothing = 3,
): { k: (number | null)[]; d: (number | null)[] } {
  // Fast %K: raw stochastic over kLength bars
  const fastK: (number | null)[] = []
  for (let i = 0; i < closes.length; i++) {
    if (i < kLength - 1) {
      fastK.push(null)
      continue
    }
    const windowHigh = Math.max(...highs.slice(i - kLength + 1, i + 1))
    const windowLow = Math.min(...lows.slice(i - kLength + 1, i + 1))
    const denom = windowHigh - windowLow
    fastK.push(denom === 0 ? 50 : ((closes[i] - windowLow) / denom) * 100)
  }

  // Slow %K: SMA(kSmoothing) of fast %K
  const firstFastK = fastK.findIndex((v) => v !== null)
  const rawK = sma(fastK.slice(firstFastK) as number[], kSmoothing)
  const k: (number | null)[] = fastK.map((v, i) =>
    v === null ? null : rawK[i - firstFastK] ?? null,
  )

  // %D: SMA(dSmoothing) of slow %K
  const firstK = k.findIndex((v) => v !== null)
  const rawD = sma(k.slice(firstK) as number[], dSmoothing)
  const d: (number | null)[] = k.map((v, i) =>
    v === null ? null : rawD[i - firstK] ?? null,
  )

  return { k, d }
}
