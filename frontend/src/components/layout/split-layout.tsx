import { PortfolioStrip } from '#/components/portfolio/portfolio-strip'
import { ChartPanel } from './chart-panel'

interface SplitLayoutProps {
  symbol: string
  chartLabel?: string
}

export function SplitLayout({ symbol, chartLabel }: SplitLayoutProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="h-3/4 min-h-0">
        <ChartPanel symbol={symbol} label={chartLabel} />
      </div>
      <div className="h-1/4 min-h-0">
        <PortfolioStrip />
      </div>
    </div>
  )
}
