import { useCallback, useState } from 'react'
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  createChart,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { Candle } from '#/lib/mock-ohlcv'
import { macd as computeMacd, sma, stochastic } from '#/lib/indicators'

interface CandlestickChartProps {
  data: Candle[]
  avgPrice?: number
  lots?: number
}

const UP_COLOR = '#22c55e'
const DOWN_COLOR = '#ef4444'
const UP_VOLUME = 'rgba(34, 197, 94, 0.35)'
const DOWN_VOLUME = 'rgba(239, 68, 68, 0.35)'
const MACD_LINE = '#60a5fa'
const MACD_SIGNAL = '#f87171'
const STOCH_K = '#60a5fa'
const STOCH_D = '#f87171'
const GRID = 'rgba(255, 255, 255, 0.05)'

const MA_CONFIG: Array<{ period: number; color: string }> = [
  { period: 3, color: '#f472b6' },
  { period: 5, color: '#c084fc' },
  { period: 20, color: '#fb923c' },
  { period: 50, color: '#4ade80' },
  { period: 100, color: '#60a5fa' },
  { period: 200, color: '#a855f7' },
]

const PANE_PRICE = 0
const PANE_MACD_VOL = 1
const PANE_STOCH = 2

export function CandlestickChart({ data, avgPrice, lots }: CandlestickChartProps) {
  const [badgeY, setBadgeY] = useState<number | null>(null)

  const lastClose = data.at(-1)?.close ?? null
  const pnlPct =
    avgPrice && lastClose ? ((lastClose - avgPrice) / avgPrice) * 100 : null

  const attachChart = useCallback(
    (node: HTMLDivElement | null) => {
      if (!node) return

      const chart = createChart(node, {
        autoSize: true,
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: 'rgba(255,255,255,0.65)',
          panes: {
            separatorColor: 'rgba(255,255,255,0.08)',
            separatorHoverColor: 'rgba(255,255,255,0.16)',
            enableResize: true,
          },
        },
        grid: {
          vertLines: { color: GRID },
          horzLines: { color: GRID },
        },
        timeScale: { borderVisible: false },
        rightPriceScale: { borderVisible: false },
        crosshair: {
          vertLine: { color: 'rgba(255,255,255,0.2)', width: 1, style: 3 },
          horzLine: { color: 'rgba(255,255,255,0.2)', width: 1, style: 3 },
        },
      })

      const times = data.map((c) => c.time as UTCTimestamp)
      const closes = data.map((c) => c.close)
      const highs = data.map((c) => c.high)
      const lows = data.map((c) => c.low)

      // ── Price pane: candles ─────────────────────────────────────
      const candleSeries = chart.addSeries(
        CandlestickSeries,
        {
          upColor: UP_COLOR,
          downColor: DOWN_COLOR,
          borderVisible: false,
          wickUpColor: UP_COLOR,
          wickDownColor: DOWN_COLOR,
        },
        PANE_PRICE,
      )
      candleSeries.setData(
        data.map((c) => ({
          time: c.time as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      )
      if (avgPrice) {
        candleSeries.createPriceLine({
          price: avgPrice,
          color: 'rgba(255,255,255,0.5)',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '',
        })
      }

      // ── Price pane: moving averages ─────────────────────────────
      for (const { period, color } of MA_CONFIG) {
        const values = sma(closes, period)
        const maSeries = chart.addSeries(
          LineSeries,
          {
            color,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: true,
            title: `MA${period}`,
          },
          PANE_PRICE,
        )
        maSeries.setData(
          times
            .map((t, i) => ({ time: t, value: values[i] }))
            .filter((p): p is { time: UTCTimestamp; value: number } =>
              p.value !== null,
            ),
        )
      }

      // ── MACD + Volume combined pane ─────────────────────────────
      const volumeSeries = chart.addSeries(
        HistogramSeries,
        {
          priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
          priceLineVisible: false,
          lastValueVisible: false,
        },
        PANE_MACD_VOL,
      )
      volumeSeries.setData(
        data.map((c) => ({
          time: c.time as UTCTimestamp,
          value: c.volume,
          color: c.close >= c.open ? UP_VOLUME : DOWN_VOLUME,
        })),
      )
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.7, bottom: 0 },
      })

      const { macd, signal } = computeMacd(closes)
      const macdLine = chart.addSeries(
        LineSeries,
        {
          color: MACD_LINE,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: 'MACD',
        },
        PANE_MACD_VOL,
      )
      macdLine.setData(
        times
          .map((t, i) => ({ time: t, value: macd[i] }))
          .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null),
      )
      macdLine.priceScale().applyOptions({
        scaleMargins: { top: 0.05, bottom: 0.05 },
      })

      const macdSignal = chart.addSeries(
        LineSeries,
        {
          color: MACD_SIGNAL,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: 'Signal',
        },
        PANE_MACD_VOL,
      )
      macdSignal.setData(
        times
          .map((t, i) => ({ time: t, value: signal[i] }))
          .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null),
      )

      // ── Stochastic pane ─────────────────────────────────────────
      const { k, d } = stochastic(highs, lows, closes)
      const stochK = chart.addSeries(
        LineSeries,
        {
          color: STOCH_K,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: '%K',
          autoscaleInfoProvider: () => ({
            priceRange: { minValue: 0, maxValue: 100 },
          }),
        },
        PANE_STOCH,
      )
      stochK.setData(
        times
          .map((t, i) => ({ time: t, value: k[i] }))
          .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null),
      )
      const stochD = chart.addSeries(
        LineSeries,
        {
          color: STOCH_D,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: '%D',
        },
        PANE_STOCH,
      )
      stochD.setData(
        times
          .map((t, i) => ({ time: t, value: d[i] }))
          .filter((p): p is { time: UTCTimestamp; value: number } => p.value !== null),
      )

      for (const { price, color } of [
        { price: 80, color: 'rgba(255,255,255,0.25)' },
        { price: 20, color: 'rgba(255,255,255,0.25)' },
      ]) {
        stochK.createPriceLine({
          price,
          color,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '',
        })
      }

      const panes = chart.panes()
      if (panes.length >= 3) {
        panes[PANE_PRICE].setStretchFactor(6)
        panes[PANE_MACD_VOL].setStretchFactor(3)
        panes[PANE_STOCH].setStretchFactor(2)
      }

      // ── Badge Y tracking ────────────────────────────────────────
      function updateBadgeY() {
        if (!avgPrice) return
        const y = candleSeries.priceToCoordinate(avgPrice)
        setBadgeY(y ?? null)
      }

      updateBadgeY()
      chart.timeScale().subscribeVisibleLogicalRangeChange(updateBadgeY)
      chart.subscribeCrosshairMove(updateBadgeY)

      const totalBars = data.length
      const rafId = requestAnimationFrame(() => {
        chart.timeScale().setVisibleLogicalRange({
          from: Math.max(0, totalBars - 120),
          to: totalBars - 1,
        })
        updateBadgeY()
      })

      return () => {
        cancelAnimationFrame(rafId)
        chart.timeScale().unsubscribeVisibleLogicalRangeChange(updateBadgeY)
        chart.unsubscribeCrosshairMove(updateBadgeY)
        chart.remove()
      }
    },
    [data, avgPrice, lots],
  )

  return (
    <div className="relative h-full w-full">
      <div ref={attachChart} className="h-full w-full" />
      {avgPrice && badgeY !== null && (
        <div
          className="pointer-events-none absolute flex items-center gap-2 rounded bg-zinc-900 px-2 py-0.5 text-xs z-1"
          style={{ top: badgeY ?? 0, left: '50%', transform: 'translate(-50%, -50%)' }}
        >
          <span className="text-white/60">{lots}L</span>
          {pnlPct !== null && (
            <span
              className={
                pnlPct >= 0 ? 'font-medium text-emerald-400' : 'font-medium text-red-400'
              }
            >
              {pnlPct >= 0 ? '+' : ''}
              {pnlPct.toFixed(2)}%
            </span>
          )}
        </div>
      )}
    </div>
  )
}
