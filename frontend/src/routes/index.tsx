import { createFileRoute } from '@tanstack/react-router'
import { SplitLayout } from '#/components/layout/split-layout'
import { fetchOhlcv } from '#/lib/api'

export const Route = createFileRoute('/')({
  loader: ({ context }) =>
    context.queryClient.ensureQueryData({
      queryKey: ['ohlcv', '^JKSE', 'D'],
      queryFn: () => fetchOhlcv('^JKSE', 730),
    }),
  component: Home,
})

function Home() {
  return (
    <SplitLayout
      symbol="^JKSE"
      chartLabel="IDX Composite"
      sessionKey="home"
      contextLabel="General"
    />
  )
}
