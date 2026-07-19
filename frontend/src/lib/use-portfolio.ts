import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface PortfolioPosition {
  ticker: string
  lots: number
  avgPrice: number
}

interface PortfolioStore {
  positions: PortfolioPosition[]
  add: (position: PortfolioPosition) => void
  remove: (ticker: string) => void
  update: (ticker: string, patch: Partial<Omit<PortfolioPosition, 'ticker'>>) => void
}

const STORAGE_KEY = import.meta.env.PORTOFOLIO_STORAGE_KEY as string

// Migrates old format (raw array) to Zustand's persist envelope on first read
const migratingStorage = createJSONStorage(() => ({
  getItem: (name: string) => {
    const raw = localStorage.getItem(name)
    if (!raw) return null
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        return JSON.stringify({ state: { positions: parsed }, version: 0 })
      }
    } catch {}
    return raw
  },
  setItem: (name: string, value: string) => localStorage.setItem(name, value),
  removeItem: (name: string) => localStorage.removeItem(name),
}))

export const usePortfolio = create<PortfolioStore>()(
  persist(
    (set) => ({
      positions: [],
      add: (position) =>
        set((s) => ({ positions: [...s.positions, position] })),
      remove: (ticker) =>
        set((s) => ({ positions: s.positions.filter((p) => p.ticker !== ticker) })),
      update: (ticker, patch) =>
        set((s) => ({
          positions: s.positions.map((p) => (p.ticker === ticker ? { ...p, ...patch } : p)),
        })),
    }),
    { name: STORAGE_KEY, storage: migratingStorage },
  ),
)
