import { createFileRoute } from '@tanstack/react-router'
import { SplitLayout } from '#/components/layout/split-layout'
import { fetchOhlcv } from '#/lib/api'

export const Route = createFileRoute('/$ticker')({
  loader: ({ context, params }) => {
    const symbol = params.ticker.toUpperCase()
    return context.queryClient.ensureQueryData({
      queryKey: ['ohlcv', symbol, 'D'],
      queryFn: () => fetchOhlcv(symbol, 730),
    })
  },
  component: TickerPage,
})

function TickerPage() {
  const { ticker } = Route.useParams()
  const symbol = ticker.toUpperCase()

  return (
    <SplitLayout
      symbol={symbol}
      chartLabel="Ticker"
      sessionKey={symbol.toLowerCase()}
      contextLabel={symbol}
    />
  )
}
