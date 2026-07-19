export interface PortfolioPosition {
  ticker: string
  lots: number
  avgPrice: number
}

export const MOCK_PORTFOLIO: PortfolioPosition[] = [
  { ticker: 'BBCA', lots: 10, avgPrice: 9200 },
  { ticker: 'BBRI', lots: 50, avgPrice: 4100 },
  { ticker: 'TLKM', lots: 30, avgPrice: 3000 },
  { ticker: 'MYOR', lots: 20, avgPrice: 2400 },
  { ticker: 'UNVR', lots: 15, avgPrice: 2100 },
  { ticker: 'ICBP', lots: 8, avgPrice: 10800 },
]
