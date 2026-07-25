import { createFileRoute } from '@tanstack/react-router'
import { SplitLayout } from '#/components/layout/split-layout'
import { fetchOhlcv } from '#/lib/api'
import { getChatHistoryFn } from '#/lib/server-fns'

export const Route = createFileRoute('/_main/$ticker')({
  loader: ({ context, params }) => {
    const symbol = params.ticker.toUpperCase()
    return Promise.all([
      context.queryClient.ensureQueryData({
        queryKey: ['ohlcv', symbol, 'D'],
        queryFn: () => fetchOhlcv(symbol, 730),
      }),
      context.queryClient.ensureQueryData({
        queryKey: ['chat-history'],
        queryFn: () => getChatHistoryFn(),
      }),
    ])
  },
  component: TickerPage,
})

function TickerPage() {
  const { ticker } = Route.useParams()
  const symbol = ticker.toUpperCase()

  return (
    <SplitLayout symbol={symbol} chartLabel="Ticker" />
  )
}
