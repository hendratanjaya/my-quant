import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addPortfolio,
  deletePortfolio,
  fetchPortfolio,
  patchPortfolio,
  type Position,
} from './portfolio-api'

export type PortfolioPosition = Position

const KEY = ['portfolio'] as const
const LEGACY_STORAGE_KEY = import.meta.env.PORTOFOLIO_STORAGE_KEY as string | undefined

async function migrateLegacyOnce(server: Position[]): Promise<void> {
  if (server.length > 0 || !LEGACY_STORAGE_KEY) return
  const raw = localStorage.getItem(LEGACY_STORAGE_KEY)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    const positions: Position[] = Array.isArray(parsed)
      ? parsed
      : (parsed?.state?.positions ?? [])
    for (const p of positions) {
      try {
        await addPortfolio(p)
      } catch {
        // ignore individual failures — best-effort migration
      }
    }
    localStorage.removeItem(LEGACY_STORAGE_KEY)
  } catch {
    // ignore malformed legacy payloads
  }
}

export function usePortfolio() {
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: KEY,
    queryFn: async () => {
      const server = await fetchPortfolio()
      await migrateLegacyOnce(server)
      return server.length === 0 && LEGACY_STORAGE_KEY ? await fetchPortfolio() : server
    },
    staleTime: 30_000,
  })

  const add = useMutation({
    mutationFn: addPortfolio,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const remove = useMutation({
    mutationFn: (ticker: string) => deletePortfolio(ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  const update = useMutation({
    mutationFn: ({ ticker, patch }: { ticker: string; patch: Partial<Omit<Position, 'ticker'>> }) =>
      patchPortfolio(ticker, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })

  return {
    positions: query.data ?? [],
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    refetch: () => qc.invalidateQueries({ queryKey: KEY }),
    add: (p: Position) => add.mutate(p),
    remove: (ticker: string) => remove.mutate(ticker),
    update: (ticker: string, patch: Partial<Omit<Position, 'ticker'>>) =>
      update.mutate({ ticker, patch }),
  }
}
