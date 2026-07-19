import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '#/components/ui/resizable'
import { PortfolioStrip } from '#/components/portfolio/portfolio-strip'
import { ChartPanel } from './chart-panel'
import { ChatPanel } from './chat-panel'

interface SplitLayoutProps {
  symbol: string
  chartLabel?: string
  sessionKey: string
  contextLabel: string
}

export function SplitLayout({
  symbol,
  chartLabel,
  sessionKey,
  contextLabel,
}: SplitLayoutProps) {
  return (
    <ResizablePanelGroup className="h-screen">
      <ResizablePanel defaultSize={65} minSize={30}>
        <div className="flex h-full flex-col">
          <div className="h-3/4 min-h-0">
            <ChartPanel symbol={symbol} label={chartLabel} />
          </div>
          <div className="h-1/4 min-h-0">
            <PortfolioStrip />
          </div>
        </div>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={35} minSize={25}>
        <ChatPanel sessionKey={sessionKey} contextLabel={contextLabel} />
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
