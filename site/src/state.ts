import type { Signals } from './types'

export type ViewMode = 'settled' | 'preview'

export interface AppState {
  settled: Signals
  preview: Signals | null
  view: ViewMode
}

function isFresher(preview: Signals, settled: Signals): boolean {
  return new Date(preview.generated_utc).getTime() > new Date(settled.generated_utc).getTime()
}

export async function loadState(): Promise<AppState> {
  const base = import.meta.env.BASE_URL

  const settledResp = await fetch(`${base}data/signals.json`, { cache: 'no-store' })
  if (!settledResp.ok) throw new Error(`failed to load signals.json (${settledResp.status})`)
  const settled: Signals = await settledResp.json()

  let preview: Signals | null = null
  try {
    const previewResp = await fetch(`${base}data/preview.json`, { cache: 'no-store' })
    if (previewResp.ok) preview = await previewResp.json()
  } catch {
    preview = null
  }

  const view: ViewMode = preview && isFresher(preview, settled) ? 'preview' : 'settled'
  return { settled, preview, view }
}

export function activeSignals(state: AppState): Signals {
  return state.view === 'preview' && state.preview ? state.preview : state.settled
}
