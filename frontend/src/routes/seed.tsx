import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, KeyRound, Plus } from 'lucide-react'

import { listSeeded, type SeededSummary } from '#/lib/api'
import {
  clearTokenFn,
  hasTokenFn,
  saveTokenFn,
  seedTickerFn,
} from '#/lib/server-fns'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { Textarea } from '#/components/ui/textarea'

export const Route = createFileRoute('/seed')({
  loader: ({ context }) =>
    context.queryClient.ensureQueryData({
      queryKey: ['auth'],
      queryFn: () => hasTokenFn(),
    }),
  component: SeedPage,
})

function SeedPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const authQuery = useQuery({
    queryKey: ['auth'],
    queryFn: () => hasTokenFn(),
  })
  const hasToken = authQuery.data?.hasToken ?? false

  const { data: seeded = [], isPending } = useQuery({
    queryKey: ['seeded'],
    queryFn: listSeeded,
  })

  const saveTokenMutation = useMutation({
    mutationFn: (token: string) => saveTokenFn({ data: token }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] })
    },
  })

  const addMutation = useMutation({
    mutationFn: (symbol: string) => seedTickerFn({ data: symbol }),
    onSuccess: (result) => {
      if (result.ok) {
        setAddOpen(false)
        setAddError(null)
        queryClient.invalidateQueries({ queryKey: ['seeded'] })
        return
      }
      if (result.error === 'unauthorized') {
        clearTokenFn().finally(() => {
          queryClient.invalidateQueries({ queryKey: ['auth'] })
          navigate({ to: '/' })
        })
        return
      }
      if (result.error === 'already-seeded') {
        setAddError('This ticker is already in the archive.')
        return
      }
      setAddError(`Upstream error (${result.status})`)
    },
    onError: (err) => {
      setAddError((err as Error).message)
    },
  })

  return (
    <div className="min-h-screen bg-background p-8">
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Database className="h-6 w-6" />
            Seeded companies
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {isPending
              ? 'Loading…'
              : `${seeded.length} ticker${seeded.length === 1 ? '' : 's'} archived from Stockbit`}
          </p>
        </div>
        <Button
          onClick={() => {
            setAddError(null)
            setAddOpen(true)
          }}
          disabled={!hasToken}
        >
          <Plus className="mr-2 h-4 w-4" />
          Add ticker
        </Button>
      </header>

      {seeded.length === 0 && !isPending ? (
        <div className="rounded-lg border border-dashed py-16 text-center text-sm text-muted-foreground">
          No tickers seeded yet. Add one to start building the archive.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {seeded.map((s) => (
            <SeededCard key={s.symbol} summary={s} />
          ))}
        </div>
      )}

      <JwtDialog
        open={!authQuery.isPending && !hasToken}
        pending={saveTokenMutation.isPending}
        onSubmit={(token) => saveTokenMutation.mutate(token)}
      />
      <AddTickerDialog
        open={addOpen}
        onOpenChange={(v) => {
          setAddOpen(v)
          if (!v) setAddError(null)
        }}
        onSubmit={(symbol) => addMutation.mutate(symbol)}
        isPending={addMutation.isPending}
        error={addError}
      />
    </div>
  )
}

function SeededCard({ summary }: { summary: SeededSummary }) {
  const seededDate = new Date(summary.seeded_at).toLocaleString()
  return (
    <div className="rounded-lg border border-white/8 bg-white/2 p-4">
      <p className="text-lg font-semibold">{summary.symbol}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {summary.row_count.toLocaleString()} rows
        {summary.period_first && summary.period_last && (
          <>
            {' · '}
            {summary.period_first} → {summary.period_last}
          </>
        )}
      </p>
      <p className="mt-2 text-[10px] text-muted-foreground">
        seeded {seededDate}
      </p>
    </div>
  )
}

function JwtDialog({
  open,
  pending,
  onSubmit,
}: {
  open: boolean
  pending: boolean
  onSubmit: (token: string) => void
}) {
  const [token, setToken] = useState('')

  return (
    <Dialog open={open}>
      <DialogContent
        showCloseButton={false}
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
        className="sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-4 w-4" />
            Stockbit session token
          </DialogTitle>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            const trimmed = token.trim()
            if (trimmed) onSubmit(trimmed)
          }}
        >
          <p className="text-sm text-muted-foreground">
            Paste your Stockbit JWT. Stored in an httpOnly session cookie.
            I assume you understand what you do by pasting your token.
          </p>
          <Input
            value={token}
            type='password'
            onChange={(e) => setToken(e.target.value)}
            placeholder="eyJhbGciOi…"
            className=" font-mono text-xs"
            autoFocus
            disabled={pending}
          />
          <Button type="submit" disabled={!token.trim() || pending}>
            {pending ? 'Saving…' : 'Save token'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function AddTickerDialog({
  open,
  onOpenChange,
  onSubmit,
  isPending,
  error,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onSubmit: (symbol: string) => void
  isPending: boolean
  error: string | null
}) {
  const [symbol, setSymbol] = useState('')

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v)
        if (!v) setSymbol('')
      }}
    >
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Add ticker to archive</DialogTitle>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            const trimmed = symbol.trim().toUpperCase()
            if (trimmed) onSubmit(trimmed)
          }}
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Ticker</label>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="BBRI"
              autoFocus
              disabled={isPending}
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button type="submit" disabled={!symbol.trim() || isPending}>
            {isPending ? 'Seeding…' : 'Seed'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
