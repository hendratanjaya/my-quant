export type Candle = {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

function seedFromString(str: string) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash) || 1
}

function seededRandom(seed: number) {
  let s = seed
  return () => {
    s = (s * 9301 + 49297) % 233280
    return s / 233280
  }
}

const START_PRICE_BY_SYMBOL: Record<string, number> = {
  '^JKSE': 7200,
  BBRI: 4200,
  BBCA: 9500,
  TLKM: 3100,
  MYOR: 2500,
  UNVR: 2200,
  ICBP: 11000,
}

/**
 * Generates a deterministic mock OHLCV series so each symbol renders
 * consistently across reloads. Replace with real archive data when ingestion lands.
 */
export function generateMockOhlcv(symbol: string, days = 400): Candle[] {
  const rand = seededRandom(seedFromString(symbol))
  const startPrice = START_PRICE_BY_SYMBOL[symbol] ?? 1000 + rand() * 5000

  const now = Math.floor(Date.now() / 1000)
  const dayInSeconds = 86400
  const candles: Candle[] = []
  let price = startPrice

  for (let i = days - 1; i >= 0; i--) {
    const time = now - i * dayInSeconds
    const drift = (rand() - 0.48) * 0.025
    const range = 0.015 + rand() * 0.025
    const open = price
    const close = Math.max(open * (1 + drift), 1)
    const high = Math.max(open, close) * (1 + range / 2)
    const low = Math.min(open, close) * (1 - range / 2)
    const volume = Math.floor(1_000_000 + rand() * 8_000_000)
    candles.push({ time, open, high, low, close, volume })
    price = close
  }

  return candles
}
