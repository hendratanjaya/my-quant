import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Search } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { IDX_TICKERS } from '#/constants/idx-tickers'

interface TickerSearchProps {
  children: React.ReactNode
}

export function TickerSearch({ children }: TickerSearchProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const filtered = query.trim()
    ? IDX_TICKERS.filter(
        (t) =>
          t.symbol.toLowerCase().includes(query.toLowerCase()) ||
          t.name.toLowerCase().includes(query.toLowerCase()),
      )
    : IDX_TICKERS

  function select(symbol: string) {
    setOpen(false)
    setQuery('')
    navigate({ to: '/$ticker', params: { ticker: symbol.toLowerCase() } })
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v)
        if (!v) setQuery('')
      }}
    >
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent showCloseButton={false} className="gap-0 p-0 sm:max-w-md">
        <DialogTitle className="sr-only">Search Ticker</DialogTitle>
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Input
            className="h-auto border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
            placeholder="Search ticker or company..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && filtered.length > 0) select(filtered[0].symbol)
            }}
            autoFocus
          />
        </div>
        <div className="max-h-72 overflow-y-auto py-1">
          {filtered.map((t) => (
            <button
              key={t.symbol}
              className="flex w-full items-center gap-4 px-4 py-2.5 text-left hover:bg-accent"
              onClick={() => select(t.symbol)}
            >
              <span className="w-12 text-sm font-semibold">{t.symbol}</span>
              <span className="truncate text-sm text-muted-foreground">{t.name}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              No results for "{query}"
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
