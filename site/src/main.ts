import { renderAllCharts } from './charts'
import { renderAll } from './panels'
import { activeSignals, loadState, type AppState } from './state'
import './styles.css'

let appState: AppState | null = null

function render(): void {
  if (!appState) return
  const signals = activeSignals(appState)
  renderAll(appState, signals)
  renderAllCharts(signals)
}

function wireToggle(): void {
  const toggle = document.getElementById('preview-toggle') as HTMLButtonElement | null
  toggle?.addEventListener('click', () => {
    if (!appState) return
    appState.view = appState.view === 'preview' ? 'settled' : 'preview'
    render()
  })
}

async function bootstrap(): Promise<void> {
  try {
    appState = await loadState()
    wireToggle()
    render()
  } catch (err) {
    const errorBox = document.getElementById('load-error')
    if (errorBox) {
      errorBox.style.display = ''
      errorBox.textContent = `Failed to load signals: ${err instanceof Error ? err.message : String(err)}`
    }
  }
}

bootstrap()
