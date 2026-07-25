import { createFileRoute } from '@tanstack/react-router'
import { SplitLayout } from '#/components/layout/split-layout'
import { fetchOhlcv } from '#/lib/api'
import { getChatHistoryFn } from '#/lib/server-fns'

export const Route = createFileRoute('/_main/')({
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData({
        queryKey: ['ohlcv', '^JKSE', 'D'],
        queryFn: () => fetchOhlcv('^JKSE', 730),
      }),
      context.queryClient.ensureQueryData({
        queryKey: ['chat-history'],
        queryFn: () => getChatHistoryFn(),
      }),
    ]),
  component: Home,
})

function Home() {
  return (
    <SplitLayout symbol="^JKSE" chartLabel="IDX Composite" />
  )
}
