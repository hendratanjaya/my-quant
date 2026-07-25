import { createFileRoute, Outlet } from '@tanstack/react-router'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '#/components/ui/resizable'
import { ChatDrawer } from '#/components/chat/chat-drawer'

export const Route = createFileRoute('/_main')({
  component: MainLayout,
})

function MainLayout() {
  return (
    <ResizablePanelGroup className="h-screen">
      <ResizablePanel defaultSize={65} minSize={30}>
        <Outlet />
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={35} minSize={25}>
        <ChatDrawer />
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
