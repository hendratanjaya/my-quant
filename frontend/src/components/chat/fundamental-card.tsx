import type {
  FundamentalReport,
  MetricCategory,
  MetricPercentile,
  PeriodValues,
  QuarterlySeries,
} from '#/lib/api'
import {
  ComparisonChart,
  type ComparisonSeriesSpec,
} from '#/components/chart/comparison-chart'
import { cn } from '#/lib/utils'

const COMPARISON_SERIES: ComparisonSeriesSpec[] = [
  { key: 'price', label: 'Price', color: '#22c55e' },
  { key: 'eps', label: 'EPS', color: '#22d3ee' },
  { key: 'revenue', label: 'Revenue', color: '#ec4899' },
  { key: 'per', label: 'PER', color: '#84cc16' },
]

// Time-series table columns. Order dictates left→right display order in the table.
const TIME_SERIES_COLUMNS: Array<{ key: string; label: string }> = [
  { key: 'pbv', label: 'PBV' },
  { key: 'der', label: 'DER' },
  { key: 'per', label: 'PER' },
  { key: 'eps', label: 'EPS' },
  { key: 'eps_ttm', label: 'EPS TTM' },
  { key: 'sps', label: 'SPS' },
  { key: 'sps_ttm', label: 'SPS TTM' },
  { key: 'ps', label: 'P/S' },
]

interface FundamentalCardProps {
  report: FundamentalReport
}

const CATEGORY_LABEL: Record<MetricCategory, string> = {
  valuation: 'Valuation',
  quality: 'Profitability',
  growth: 'Growth (quarterly)',
  ttm: 'Growth (TTM)',
}

const CATEGORY_ORDER: MetricCategory[] = ['valuation', 'quality', 'growth', 'ttm']

export function FundamentalCard({ report }: FundamentalCardProps) {
  // Defensive against messages persisted before newer fields existed
  // (e.g. `time_series` was added after chat-store started caching to localStorage).
  const metrics = report.metrics ?? []
  const quarterly = report.quarterly ?? []
  const timeSeries = report.time_series ?? []
  const comparison = report.comparison ?? []
  const grouped = groupByCategory(metrics)

  return (
    <div className="w-full rounded-lg border border-white/8 bg-white/[0.02] p-3 text-xs">
      <header className="mb-2 flex items-baseline justify-between">
        <h3 className="text-base font-semibold">{report.symbol}</h3>
        <span className="text-[10px] text-muted-foreground">
          as of {report.as_of}
        </span>
      </header>

      {metrics.length === 0 ? (
        <p className="py-3 text-muted-foreground">{report.reading}</p>
      ) : (
        <>
          {CATEGORY_ORDER.map((cat) => {
            const rows = grouped[cat]
            if (!rows || rows.length === 0) return null
            return (
              <section key={cat} className="mb-2">
                <h4 className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  {CATEGORY_LABEL[cat]}
                </h4>
                <div className="space-y-0.5">
                  {rows.map((m) => (
                    <PercentileRow key={m.metric} metric={m} />
                  ))}
                </div>
              </section>
            )
          })}

          {quarterly.length > 0 && (
            <section className="mb-2">
              <h4 className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                Quarterly (last {quarterly[0].points.length})
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {quarterly.map((q) => (
                  <MiniSparkline key={q.metric} series={q} />
                ))}
              </div>
            </section>
          )}

          {comparison.length > 0 && (
            <section className="mb-2">
              <div className="mb-1 flex items-baseline justify-between">
                <h4 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Price &amp; EPS Historical (last {comparison.length} quarters)
                </h4>
              </div>
              <ComparisonLegend rows={comparison} series={COMPARISON_SERIES} />
              <ComparisonChart data={comparison} series={COMPARISON_SERIES} />
            </section>
          )}

          {timeSeries.length > 0 && (
            <section className="mb-2">
              <h4 className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                Value vs Growth (last {timeSeries.length} quarters)
              </h4>
              <PeriodTable rows={timeSeries} />
            </section>
          )}

          <p className="mt-3 border-t border-white/8 pt-2 text-[11px] leading-relaxed text-muted-foreground">
            {report.reading}
          </p>
        </>
      )}
    </div>
  )
}

// ── Percentile bar row ──────────────────────────────────────────────

function PercentileRow({ metric }: { metric: MetricPercentile }) {
  const color = tone(metric.percentile, metric.category)

  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 truncate">{metric.metric}</span>

      <div className="relative h-1.5 flex-1 rounded-full bg-white/8">
        <div
          className={cn('absolute top-0 h-1.5 rounded-full', color.bar)}
          style={{ left: 0, width: `${metric.percentile}%` }}
        />
        <div
          className={cn(
            'absolute top-1/2 h-2.5 w-0.5 -translate-y-1/2 rounded-full',
            color.marker,
          )}
          style={{ left: `${metric.percentile}%` }}
        />
      </div>

      <span className="w-20 shrink-0 text-right tabular-nums">
        {formatValue(metric.current)}
      </span>
      <span className="w-10 shrink-0 text-right text-[10px] tabular-nums text-muted-foreground">
        {metric.percentile.toFixed(0)}%
      </span>
    </div>
  )
}

/**
 * Percentile tone by category:
 *  - valuation: low percentile = cheap = green; high = expensive = red
 *  - quality/growth/ttm: high = strong = green; low = weak = red
 */
function tone(
  percentile: number,
  category: MetricCategory,
): { bar: string; marker: string } {
  const good =
    category === 'valuation' ? percentile <= 30 : percentile >= 70
  const bad =
    category === 'valuation' ? percentile >= 70 : percentile <= 30
  if (good) return { bar: 'bg-emerald-500/40', marker: 'bg-emerald-400' }
  if (bad) return { bar: 'bg-red-500/40', marker: 'bg-red-400' }
  return { bar: 'bg-amber-500/40', marker: 'bg-amber-400' }
}

// ── Quarterly sparkline ─────────────────────────────────────────────

function MiniSparkline({ series }: { series: QuarterlySeries }) {
  const values = series.points.map((p) => p.value)
  if (values.length === 0) return null

  const min = Math.min(...values, 0)
  const max = Math.max(...values, 0)
  const range = max - min || 1
  const latest = values[values.length - 1]
  const prev = values[values.length - 2] ?? latest
  const changed = latest - prev
  const barHeight = 64
  const zeroFromTop = (max / range) * barHeight

  return (
    <div className="rounded-md border border-white/8 bg-white/[0.02] p-2">
      <div className="mb-1.5 flex items-baseline justify-between text-[10px]">
        <span className="font-medium">{series.metric}</span>
        <span
          className={cn(
            'tabular-nums',
            changed >= 0 ? 'text-emerald-500' : 'text-red-500',
          )}
        >
          {latest.toFixed(1)}%
        </span>
      </div>

      <div
        className="grid gap-[1px]"
        style={{ gridTemplateColumns: `repeat(${values.length}, 1fr)` }}
      >
        {values.map((v, i) => {
          const magnitude = Math.abs(v / range) * barHeight
          const top =
            v >= 0 ? zeroFromTop - magnitude : zeroFromTop
          return (
            <div key={i} className="flex flex-col items-center gap-0.5">
              <div
                className="relative w-full"
                style={{ height: barHeight }}
              >
                <div
                  className={cn(
                    'absolute inset-x-0 rounded-[1px]',
                    v >= 0 ? 'bg-emerald-500/70' : 'bg-red-500/70',
                  )}
                  style={{
                    top,
                    height: Math.max(magnitude, 1),
                  }}
                />
              </div>
              <span className="text-[8px] leading-none text-muted-foreground/80 tabular-nums">
                {formatShort(v)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** Compact numeric formatter for tight bar labels. */
function formatShort(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 100) return v.toFixed(0)
  if (abs >= 10) return v.toFixed(1)
  return v.toFixed(1)
}

// ── Comparison chart legend ─────────────────────────────────────────

function ComparisonLegend({
  rows,
  series,
}: {
  rows: PeriodValues[]
  series: ComparisonSeriesSpec[]
}) {
  const latest = rows[rows.length - 1]
  if (!latest) return null
  return (
    <div className="mb-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[10px]">
      {series.map((s) => {
        const v = latest.values[s.key]
        return (
          <span key={s.key} className="flex items-center gap-1.5">
            <span
              className="h-0.5 w-3 rounded-full"
              style={{ background: s.color }}
            />
            <span className="text-muted-foreground">{s.label}</span>
            <span className="tabular-nums">{formatCell(v)}</span>
          </span>
        )
      })}
    </div>
  )
}

// ── Time-series table (Value vs Growth) ─────────────────────────────

function PeriodTable({ rows }: { rows: PeriodValues[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-white/8">
      <table className="w-full min-w-max border-collapse text-[10px]">
        <thead>
          <tr className="border-b border-white/8 bg-white/[0.03]">
            <th className="sticky left-0 z-10 bg-background px-2 py-1.5 text-left font-medium text-muted-foreground">
              Period
            </th>
            {TIME_SERIES_COLUMNS.map((col) => (
              <th
                key={col.key}
                className="px-2 py-1.5 text-right font-medium text-muted-foreground"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.period_end}
              className={cn(
                'border-t border-white/5',
                i === rows.length - 1 && 'bg-white/[0.03] font-medium',
              )}
            >
              <td className="sticky left-0 z-10 whitespace-nowrap bg-background px-2 py-1 tabular-nums">
                {row.period_end}
              </td>
              {TIME_SERIES_COLUMNS.map((col) => (
                <td
                  key={col.key}
                  className="whitespace-nowrap px-2 py-1 text-right tabular-nums"
                >
                  {formatCell(row.values[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Numeric cell formatting: raw ratios get 2 decimals, big money gets B/T suffix. */
function formatCell(v: number | null | undefined): string {
  if (v == null) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e12) return `${(v / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (abs >= 1000) return v.toLocaleString('id-ID', { maximumFractionDigits: 0 })
  return v.toFixed(2)
}

// ── Helpers ─────────────────────────────────────────────────────────

function groupByCategory(
  metrics: MetricPercentile[],
): Record<MetricCategory, MetricPercentile[]> {
  const groups: Record<MetricCategory, MetricPercentile[]> = {
    valuation: [],
    quality: [],
    growth: [],
    ttm: [],
  }
  for (const m of metrics) groups[m.category].push(m)
  return groups
}

function formatValue(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 1e12) return `${(v / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return v.toLocaleString('id-ID', { maximumFractionDigits: 0 })
  return v.toFixed(2)
}
