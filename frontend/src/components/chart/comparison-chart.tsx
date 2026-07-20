import { useCallback } from 'react'
import {
  ColorType,
  LineSeries,
  createChart,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { PeriodValues } from '#/lib/api'

export interface ComparisonSeriesSpec {
  key: string
  label: string
  color: string
}

interface ComparisonChartProps {
  data: PeriodValues[]
  series: ComparisonSeriesSpec[]
  /** Chart height in pixels. */
  height?: number
}

/**
 * Overlays multiple metrics on a single time axis. Each series is min-max
 * normalized to [0, 100] before plotting so scales like "Revenue in trillions"
 * and "PER dimensionless" can share one axis for trend comparison.
 */
export function ComparisonChart({
  data,
  series,
  height = 200,
}: ComparisonChartProps) {
  const attach = useCallback(
    (node: HTMLDivElement | null) => {
      if (!node) return

      const chart = createChart(node, {
        autoSize: true,
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: 'rgba(255,255,255,0.55)',
        },
        grid: {
          vertLines: { color: 'rgba(255,255,255,0.04)' },
          horzLines: { color: 'rgba(255,255,255,0.04)' },
        },
        timeScale: {
          borderVisible: false,
          timeVisible: false,
          secondsVisible: false,
        },
        rightPriceScale: { visible: false, borderVisible: false },
        leftPriceScale: { visible: false, borderVisible: false },
        crosshair: {
          vertLine: {
            color: 'rgba(255,255,255,0.2)',
            width: 1,
            style: 3,
          },
          horzLine: {
            color: 'rgba(255,255,255,0.2)',
            width: 1,
            style: 3,
          },
        },
      })

      for (const spec of series) {
        const points = extractSeries(data, spec.key)
        if (points.length < 2) continue
        const normalized = minMaxNormalize(points)

        const line = chart.addSeries(LineSeries, {
          color: spec.color,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        line.setData(normalized)
      }

      chart.timeScale().fitContent()

      return () => {
        chart.remove()
      }
    },
    [data, series],
  )

  return <div ref={attach} style={{ height }} className="w-full" />
}

// ── Helpers ─────────────────────────────────────────────────────────

type SeriesPoint = { time: UTCTimestamp; value: number }

function extractSeries(rows: PeriodValues[], key: string): SeriesPoint[] {
  const out: SeriesPoint[] = []
  for (const row of rows) {
    const v = row.values[key]
    if (v == null) continue
    const time = Math.floor(new Date(row.period_end).getTime() / 1000) as UTCTimestamp
    out.push({ time, value: v })
  }
  return out
}

function minMaxNormalize(points: SeriesPoint[]): SeriesPoint[] {
  const values = points.map((p) => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return points.map((p) => ({
    time: p.time,
    value: ((p.value - min) / range) * 100,
  }))
}
