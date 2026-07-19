import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CandlestickChart } from '#/components/chart/candlestick-chart'
import { TickerSearch } from '#/components/ticker-search'
import { fetchOhlcv } from '#/lib/api'
import { TIMEFRAME_DAYS, TIMEFRAME_INTERVAL, type Timeframe } from '#/lib/indicators'
import { usePortfolio } from '#/lib/use-portfolio'
import { cn } from '#/lib/utils'

interface ChartPanelProps {
  symbol: string
  label?: string
}

const TIMEFRAMES: Timeframe[] = ['D', 'W', 'M']

export function ChartPanel({ symbol, label }: ChartPanelProps) {
  const [timeframe, setTimeframe] = useState<Timeframe>('D')
  const { positions } = usePortfolio()
  const position = positions.find((p) => p.ticker === symbol.toUpperCase())

  const { data, isPending, isError } = useQuery({
    queryKey: ['ohlcv', symbol, timeframe],
    queryFn: () => fetchOhlcv(symbol, TIMEFRAME_DAYS[timeframe], TIMEFRAME_INTERVAL[timeframe]),
  })

  const last = data?.at(-1)
  const prev = data?.at(-2)
  const changePct = last && prev ? ((last.close - prev.close) / prev.close) * 100 : 0

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <TickerSearch>
          <button className="text-left transition-opacity hover:opacity-70">
            <h2 className="text-sm font-medium text-muted-foreground">
              {label ?? 'Chart'}
            </h2>
            <p className="text-lg font-semibold">{symbol}</p>
          </button>
        </TickerSearch>

        <div className="flex items-center gap-1 rounded-md border border-white/10 p-0.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={cn(
                'rounded px-2.5 py-0.5 text-xs font-medium transition-colors',
                timeframe === tf
                  ? 'bg-white/15 text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {tf}
            </button>
          ))}
        </div>

        {last && (
          <div className="text-right">
            <p className="text-lg font-semibold">
              {last.close.toLocaleString('id-ID', { maximumFractionDigits: 2 })}
            </p>
            <p className={changePct >= 0 ? 'text-sm font-medium text-emerald-500' : 'text-sm font-medium text-red-500'}>
              {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
            </p>
          </div>
        )}
      </header>
      <div className="flex-1">
        {isPending && (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Loading chart…
          </div>
        )}
        {isError && (
          <div className="flex h-full items-center justify-center text-sm text-red-500">
            Failed to load chart data
          </div>
        )}
        {data && <CandlestickChart data={data} avgPrice={position?.avgPrice} lots={position?.lots} />}
      </div>
    </div>
  )
}
