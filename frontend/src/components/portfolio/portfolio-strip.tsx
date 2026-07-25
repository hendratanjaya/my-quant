import { useCallback, useMemo, useState } from 'react'
import {
  AreaSeries,
  ColorType,
  createChart,
  type UTCTimestamp,
} from 'lightweight-charts'
import { ChevronLeft, ChevronRight, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import type { Candle } from '#/lib/mock-ohlcv'
import { fetchOhlcv } from '#/lib/api'
import { usePortfolio, type PortfolioPosition } from '#/lib/use-portfolio'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '#/components/ui/context-menu'
import { cn } from '#/lib/utils'
import { IDX_TICKERS } from '#/constants/idx-tickers'

const PAGE_SIZE = 5

export function PortfolioStrip() {
  const { positions, isFetching, refetch, add, remove, update } = usePortfolio()
  const [page, setPage] = useState(0)
  const totalPages = Math.ceil(positions.length / PAGE_SIZE)
  const visible = positions.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  if (positions.length === 0) {
    return (
      <div className="flex h-full items-center justify-center border-t">
        <AddPositionDialog onAdd={add}>
          <Button variant="outline" size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Add Position
          </Button>
        </AddPositionDialog>
      </div>
    )
  }

  return (
    <div className="h-full border-t px-3 py-2">
      <div className="flex h-full items-stretch gap-2">
        <button
          className="flex items-center text-muted-foreground transition-colors hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
          onClick={() => setPage((p) => p - 1)}
          disabled={page === 0}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="flex flex-1 gap-2">
          {visible.map((pos) => (
            <PortfolioCard
              key={pos.ticker}
              position={pos}
              onRemove={remove}
              onUpdate={update}
            />
          ))}
        </div>
        <button
          className="flex items-center text-muted-foreground transition-colors hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
          onClick={() => setPage((p) => p + 1)}
          disabled={page >= totalPages - 1}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          className="flex items-center pl-1 text-muted-foreground transition-colors hover:text-foreground disabled:opacity-30"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Reload portfolio"
        >
          <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
        </button>
        <AddPositionDialog onAdd={add}>
          <button
            className="flex items-center pl-1 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Add position"
          >
            <Plus className="h-4 w-4" />
          </button>
        </AddPositionDialog>
      </div>
    </div>
  )
}

interface AddPositionDialogProps {
  onAdd: (position: PortfolioPosition) => void
  children: React.ReactNode
}

function TickerCombobox({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return IDX_TICKERS.slice(0, 30)
    return IDX_TICKERS.filter(
      (t) =>
        t.symbol.toLowerCase().includes(q) || t.name.toLowerCase().includes(q),
    ).slice(0, 50)
  }, [query])

  function select(symbol: string) {
    onChange(symbol)
    setQuery(symbol)
    setOpen(false)
  }

  return (
    <div className="relative">
      <Input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          onChange('')
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 100)}
        placeholder="Search ticker..."
        autoComplete="off"
        autoFocus
      />
      {open && (
        <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-48 overflow-y-auto rounded-md border bg-popover shadow-md">
          {filtered.length === 0 ? (
            <p className="px-3 py-4 text-center text-sm text-muted-foreground">
              No tickers found
            </p>
          ) : (
            filtered.map((t) => (
              <button
                key={t.symbol}
                type="button"
                className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-accent"
                onMouseDown={(e) => {
                  e.preventDefault()
                  select(t.symbol)
                }}
              >
                <span className="w-12 shrink-0 text-sm font-semibold">{t.symbol}</span>
                <span className="truncate text-xs text-muted-foreground">{t.name}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function formatIDR(raw: string): string {
  // strip everything except digits and the first comma (decimal sep)
  const cleaned = raw.replace(/[^\d,]/g, '')
  const commaIdx = cleaned.indexOf(',')
  const intStr = commaIdx === -1 ? cleaned : cleaned.slice(0, commaIdx)
  const decStr = commaIdx === -1 ? null : cleaned.slice(commaIdx + 1).replace(/,/g, '').slice(0, 2)
  const intFormatted = intStr === '' ? '' : Number(intStr).toLocaleString('id-ID')
  return decStr === null ? intFormatted : `${intFormatted},${decStr}`
}

function parseIDR(formatted: string): number {
  return parseFloat(formatted.replace(/\./g, '').replace(',', '.')) || 0
}

function AddPositionDialog({ onAdd, children }: AddPositionDialogProps) {
  const [open, setOpen] = useState(false)
  const [ticker, setTicker] = useState('')
  const [lots, setLots] = useState('')
  const [avgPrice, setAvgPrice] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    const l = parseInt(lots, 10)
    const p = parseIDR(avgPrice)
    if (!t || !l || !p) return
    onAdd({ ticker: t, lots: l, avgPrice: p })
    setTicker('')
    setLots('')
    setAvgPrice('')
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Add Position</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 pt-1">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Ticker</label>
            <TickerCombobox value={ticker} onChange={setTicker} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Lots</label>
            <Input
              type="number"
              min={1}
              placeholder="e.g. 10"
              value={lots}
              onChange={(e) => setLots(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Avg Price (IDR)</label>
            <Input
              type="text"
              inputMode="decimal"
              placeholder="e.g. 9.500"
              value={avgPrice}
              onChange={(e) => setAvgPrice(formatIDR(e.target.value))}
            />
          </div>
          <Button type="submit" className="mt-1">
            Add
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function SparklineChart({ candles, isUp }: { candles: Candle[]; isUp: boolean }) {
  const lineColor = isUp ? '#22c55e' : '#ef4444'
  const topColor = isUp ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'

  const attachChart = useCallback(
    (node: HTMLDivElement | null) => {
      if (!node) return

      const chart = createChart(node, {
        autoSize: true,
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          attributionLogo: false,
        },
        leftPriceScale: { visible: false },
        rightPriceScale: { visible: false },
        timeScale: { visible: false },
        grid: {
          vertLines: { color: 'rgba(255,255,255,0.04)' },
          horzLines: { color: 'rgba(255,255,255,0.04)' },
        },
        crosshair: {
          vertLine: { visible: false },
          horzLine: { visible: false },
        },
        handleScroll: false,
        handleScale: false,
      })

      const series = chart.addSeries(AreaSeries, {
        lineColor,
        topColor,
        bottomColor: 'transparent',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })

      series.setData(
        candles.map((c) => ({
          time: c.time as UTCTimestamp,
          value: c.close,
        })),
      )

      chart.timeScale().fitContent()

      return () => chart.remove()
    },
    [candles, lineColor, topColor],
  )

  return <div ref={attachChart} className="h-full w-full" />
}

function EditPositionDialog({
  open,
  onOpenChange,
  position,
  onSave,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  position: PortfolioPosition
  onSave: (patch: Partial<Omit<PortfolioPosition, 'ticker'>>) => void
}) {
  const [lots, setLots] = useState(String(position.lots))
  const [avgPrice, setAvgPrice] = useState(
    formatIDR(String(position.avgPrice).replace('.', ',')),
  )

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const l = parseInt(lots, 10)
    const p = parseIDR(avgPrice)
    if (!l || !p) return
    onSave({ lots: l, avgPrice: p })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Edit {position.ticker}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 pt-1">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Lots</label>
            <Input
              type="number"
              min={1}
              value={lots}
              onChange={(e) => setLots(e.target.value)}
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Avg Price (IDR)</label>
            <Input
              type="text"
              inputMode="decimal"
              value={avgPrice}
              onChange={(e) => setAvgPrice(formatIDR(e.target.value))}
            />
          </div>
          <Button type="submit" className="mt-1">
            Save
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function PortfolioCard({
  position,
  onRemove,
  onUpdate,
}: {
  position: PortfolioPosition
  onRemove: (ticker: string) => void
  onUpdate: (ticker: string, patch: Partial<Omit<PortfolioPosition, 'ticker'>>) => void
}) {
  const { ticker } = position
  const [editOpen, setEditOpen] = useState(false)

  const { data } = useQuery({
    queryKey: ['ohlcv', ticker],
    queryFn: () => fetchOhlcv(ticker),
  })

  const last = data?.at(-1)
  const prev = data?.at(-2)
  const changePct = last && prev ? ((last.close - prev.close) / prev.close) * 100 : null
  const isUp = changePct !== null ? changePct >= 0 : true
  const recentCandles = data ? data.slice(-30) : []

  return (
    <>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <Link
            to="/$ticker"
            params={{ ticker: ticker.toLowerCase() }}
            className={cn(
              'relative flex flex-1 flex-col overflow-hidden rounded-lg border border-white/8 px-3 py-2',
              'bg-liner-to-b from-white/5 to-transparent',
              'transition-colors hover:border-white/20 hover:from-white/8',
            )}
          >
            <div
              className={cn(
                'absolute inset-x-0 top-0 h-0.5',
                changePct === null ? 'bg-white/10' : isUp ? 'bg-emerald-500/70' : 'bg-red-500/70',
              )}
            />
            <div className="flex items-start justify-between gap-2 pt-1">
              <div>
                <span className="text-xs font-semibold">{ticker}</span>
                <p className="text-[10px] text-muted-foreground">
                  {position.lots}L &middot; {position.avgPrice.toLocaleString('id-ID', { maximumFractionDigits: 2 })}
                </p>
              </div>
              <div className="text-right">
                {last ? (
                  <>
                    <p className="text-sm font-bold tabular-nums">
                      {last.close.toLocaleString('id-ID', { maximumFractionDigits: 0 })}
                    </p>
                    {changePct !== null && (
                      <span
                        className={cn(
                          'text-xs font-medium',
                          isUp ? 'text-emerald-500' : 'text-red-500',
                        )}
                      >
                        {isUp ? '+' : ''}
                        {changePct.toFixed(2)}%
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-xs text-muted-foreground">…</span>
                )}
              </div>
            </div>

            <div className="min-h-0 flex-1 pt-1">
              {recentCandles.length > 0 && (
                <SparklineChart candles={recentCandles} isUp={isUp} />
              )}
            </div>
          </Link>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onSelect={() => setEditOpen(true)}>
            <Pencil />
            Edit
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem variant="destructive" onSelect={() => onRemove(ticker)}>
            <Trash2 />
            Delete
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      <EditPositionDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        position={position}
        onSave={(patch) => onUpdate(ticker, patch)}
      />
    </>
  )
}
