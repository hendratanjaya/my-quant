export function ActivityIndicator({ text }: { text: string | null }) {
  if (!text) return null
  return (
    <div className="text-xs text-muted-foreground italic px-3 py-1 flex items-center gap-2">
      <span className="inline-block w-2 h-2 rounded-full bg-primary/60 animate-pulse" />
      {text}
    </div>
  )
}
