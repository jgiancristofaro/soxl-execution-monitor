import {
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  ScatterController,
  Tooltip,
} from 'chart.js'
import type { Signals } from './types'

Chart.register(
  CategoryScale,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  ScatterController,
  Legend,
  Tooltip,
  Filler
)

const GRID_COLOR = 'rgba(148, 163, 184, 0.12)'
const TEXT_COLOR = '#9ca3af'

// Chart.js's per-type generics don't unify well across our four distinct chart configs;
// widen to `any` at this one boundary rather than fighting the type system for a thin wrapper.
const existingCharts = new Map<string, Chart<any, any, any>>()

function renderChart(canvasId: string, config: any): void {
  const canvas = document.getElementById(canvasId) as HTMLCanvasElement | null
  if (!canvas) return

  existingCharts.get(canvasId)?.destroy()

  const chart = new Chart(canvas, {
    ...config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR, maxTicksLimit: 8 } },
        y: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
      },
      plugins: { legend: { labels: { color: TEXT_COLOR } } },
      ...config.options,
    },
  })
  existingCharts.set(canvasId, chart)
}

export function renderSoxlChart(s: Signals): void {
  const markDates = new Set(s.series.tranche_marks.map((m) => m.date))
  const markPoints = s.series.dates.map((d, i) => (markDates.has(d) ? s.series.soxl_close[i] : null))

  renderChart('chart-soxl', {
    type: 'line',
    data: {
      labels: s.series.dates,
      datasets: [
        {
          label: 'SOXL close',
          data: s.series.soxl_close,
          borderColor: '#38bdf8',
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 1.5,
        },
        {
          label: 'Tranche fill',
          data: markPoints,
          borderColor: '#f59e0b',
          backgroundColor: '#f59e0b',
          pointRadius: 6,
          pointStyle: 'triangle',
          showLine: false,
        },
      ],
    },
  })
}

export function renderRv20Chart(s: Signals): void {
  const n = s.series.dates.length
  renderChart('chart-rv20', {
    type: 'line',
    data: {
      labels: s.series.dates,
      datasets: [
        { label: 'rv20', data: s.series.rv20, borderColor: '#38bdf8', backgroundColor: 'transparent', pointRadius: 0, borderWidth: 1.5 },
        { label: 'rv20 p90', data: s.series.rv20_p90, borderColor: '#a78bfa', backgroundColor: 'transparent', pointRadius: 0, borderWidth: 1.5, borderDash: [4, 3] },
        { label: '0.55', data: Array(n).fill(0.55), borderColor: '#34d399', backgroundColor: 'transparent', pointRadius: 0, borderWidth: 1, borderDash: [2, 2] },
        { label: '0.60', data: Array(n).fill(0.60), borderColor: '#fbbf24', backgroundColor: 'transparent', pointRadius: 0, borderWidth: 1, borderDash: [2, 2] },
        { label: '0.65', data: Array(n).fill(0.65), borderColor: '#f87171', backgroundColor: 'transparent', pointRadius: 0, borderWidth: 1, borderDash: [2, 2] },
      ],
    },
  })
}

export function renderETargetChart(s: Signals): void {
  renderChart('chart-etarget', {
    type: 'line',
    data: {
      labels: s.series.dates,
      datasets: [
        {
          label: 'E_target',
          data: s.series.e_target,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.08)',
          fill: true,
          stepped: true,
          pointRadius: 0,
          borderWidth: 1.5,
        },
      ],
    },
  })
}

export function renderAttributionChart(s: Signals): void {
  renderChart('chart-attribution', {
    type: 'line',
    data: {
      labels: s.series.dates,
      datasets: [
        {
          label: 'Engine equity (hypothetical always-at-target)',
          data: s.series.equity_engine,
          borderColor: '#38bdf8',
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 1.5,
          spanGaps: false,
        },
        {
          label: 'SOXL buy-and-hold',
          data: s.series.equity_bh,
          borderColor: '#9ca3af',
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 1.5,
          spanGaps: false,
        },
      ],
    },
  })
}

export function renderAllCharts(s: Signals): void {
  renderSoxlChart(s)
  renderRv20Chart(s)
  renderETargetChart(s)
  renderAttributionChart(s)
}
