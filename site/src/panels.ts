import type { AppState } from './state'
import type { Signals, Tranche } from './types'

function $(id: string): HTMLElement {
  const el = document.getElementById(id)
  if (!el) throw new Error(`missing element #${id}`)
  return el
}

function pct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  return `${(v * 100).toFixed(digits)}%`
}

function num(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  return v.toFixed(digits)
}

function setBadge(el: HTMLElement, text: string, color: 'green' | 'amber' | 'red' | 'grey'): void {
  el.textContent = text
  el.className = `badge badge-${color}`
  el.style.display = ''
}

export function renderHeader(state: AppState, s: Signals): void {
  $('last-session').textContent = `Last session: ${s.last_session}`

  const staleBadge = $('stale-badge')
  staleBadge.style.display = s.data_stale ? '' : 'none'

  const previewBanner = $('preview-banner')
  previewBanner.style.display = s.is_preview ? '' : 'none'

  const toggle = $('preview-toggle') as HTMLButtonElement
  if (state.preview) {
    toggle.style.display = ''
    toggle.textContent = state.view === 'preview' ? 'Switch to SETTLED' : 'Switch to PREVIEW'
  } else {
    toggle.style.display = 'none'
  }

  $('soxx-close').textContent = s.market.soxx_close.toFixed(2)
  $('soxl-close').textContent = s.market.soxl_close.toFixed(2)
  $('soxx-ret').textContent = pct(s.market.soxx_ret)
  $('soxl-ret').textContent = pct(s.market.soxl_ret)

  $('tripwire-banner').style.display = s.tripwires.any ? '' : 'none'

  const breachBanner = $('cap-breach-banner')
  if (s.caps.sleeve_breach) {
    breachBanner.style.display = ''
    breachBanner.textContent = `SLEEVE CAP BREACHED (BREACH-FLAT) — blended P&L ${pct(s.caps.sleeve_pnl)}`
  } else if (s.caps.tranche_breaches.length > 0) {
    breachBanner.style.display = ''
    breachBanner.textContent = `Tranche cap breached (BREACH-HALVE): ${s.caps.tranche_breaches.join(', ')}`
  } else {
    breachBanner.style.display = 'none'
  }
}

export function renderGauge(s: Signals): void {
  $('e-target-number').textContent = num(s.engine.e_target)

  const fill = $('gauge-fill')
  fill.style.width = `${Math.min(100, Math.max(0, s.engine.e_target * 100))}%`
  const marker = $('gauge-deployed-marker')
  marker.style.left = `${Math.min(100, Math.max(0, s.engine.deployed * 100))}%`

  const flag = $('act-hold-flag')
  flag.textContent = s.engine.act ? 'ACT' : 'HOLD'
  flag.className = `act-flag ${s.engine.act ? 'act-flag-act' : 'act-flag-hold'}`

  $('act-instruction').style.display = s.engine.act ? '' : 'none'

  const rulesRow = $('rules-row')
  rulesRow.innerHTML = ''
  for (const [name, value] of Object.entries(s.engine.rules)) {
    const el = document.createElement('span')
    el.className = 'rule-chip'
    el.textContent = `${name}: ${num(value)}`
    rulesRow.appendChild(el)
  }

  $('gate-t').textContent = num(s.engine.gate.T, 1)
  const gateState = s.engine.gate.T === 1.0 ? 'OPEN' : s.engine.gate.T === 0.5 ? 'HALF' : 'CLOSED'
  $('gate-state').textContent = gateState
  $('deployed-value').textContent = pct(s.engine.deployed)
  $('gap-value').textContent = pct(s.engine.gap)
}

function trancheStatusColor(status: Tranche['status']): 'green' | 'amber' | 'red' | 'grey' {
  if (status === 'DEPLOYED') return 'green'
  if (status === 'ARMED') return 'amber'
  if (status === 'SKIPPED') return 'grey'
  return 'grey'
}

export function renderTranches(s: Signals): void {
  const container = $('tranche-rows')
  container.innerHTML = ''

  const allDeployed = s.tranches.every((t) => t.status === 'DEPLOYED')
  if (allDeployed) {
    const badge = document.createElement('div')
    badge.className = 'badge badge-green engine-governs'
    badge.textContent = 'ENGINE GOVERNS'
    container.appendChild(badge)
    return
  }

  for (const t of s.tranches) {
    const row = document.createElement('div')
    row.className = 'tranche-row'

    const header = document.createElement('div')
    header.className = 'tranche-header'
    const badge = document.createElement('span')
    setBadge(badge, `${t.id} · ${t.status}`, trancheStatusColor(t.status))
    header.appendChild(badge)

    const pctSpan = document.createElement('span')
    pctSpan.textContent = t.pct !== null ? `${(t.pct * 100).toFixed(0)}% of C` : 'sized at fill'
    header.appendChild(pctSpan)

    if (t.pnl !== null) {
      const pnlSpan = document.createElement('span')
      pnlSpan.textContent = `P&L: ${pct(t.pnl)}`
      pnlSpan.className = t.pnl <= 0 ? 'pnl-negative' : 'pnl-positive'
      header.appendChild(pnlSpan)
    }
    row.appendChild(header)

    const triggers = document.createElement('div')
    triggers.className = 'trigger-chips'
    for (const trig of t.triggers) {
      const chip = document.createElement('span')
      chip.className = `chip-trigger ${trig.pass ? 'chip-pass' : 'chip-fail'}`
      chip.textContent = `${trig.pass ? '✓' : '✗'} ${trig.name}`
      triggers.appendChild(chip)
    }
    row.appendChild(triggers)

    container.appendChild(row)
  }
}

export function renderCaps(s: Signals): void {
  const container = $('caps-rows')
  container.innerHTML = ''
  const deployed = s.tranches.filter((t) => t.status === 'DEPLOYED')
  if (deployed.length === 0) {
    container.innerHTML = '<div class="empty-note">No deployed tranches yet.</div>'
  }
  for (const t of deployed) {
    const row = document.createElement('div')
    row.className = 'caps-row'
    const breached = s.caps.tranche_breaches.includes(t.id)
    const badge = document.createElement('span')
    setBadge(badge, breached ? 'BREACH-HALVE' : 'OK', breached ? 'red' : 'green')

    const idSpan = document.createElement('span')
    idSpan.textContent = t.id
    const pnlSpan = document.createElement('span')
    pnlSpan.textContent = `P&L: ${pct(t.pnl)}`

    row.appendChild(idSpan)
    row.appendChild(pnlSpan)
    row.appendChild(badge)
    container.appendChild(row)
  }

  $('sleeve-pnl').textContent = pct(s.caps.sleeve_pnl)
  setBadge(
    $('sleeve-status'),
    s.caps.sleeve_breach ? 'BREACH-FLAT' : 'OK',
    s.caps.sleeve_breach ? 'red' : 'green'
  )
}

export function renderVRP(s: Signals): void {
  $('iv30-value').textContent = s.vrp.iv30 !== null ? pct(s.vrp.iv30) : '--'
  $('vrp-rv20').textContent = pct(s.engine.rv20)
  $('vrp-value').textContent = s.vrp.vrp !== null ? pct(s.vrp.vrp) : '--'
  $('vrp-stale-badge').style.display = s.vrp.stale ? '' : 'none'

  const zoneEl = $('vrp-zone-label')
  if (s.vrp.zone === 'BUY_OPTIONALITY') {
    zoneEl.textContent = 'BUY OPTIONALITY (calls/puts cheap vs realized — never sell options here)'
    zoneEl.className = 'zone-label zone-buy'
  } else if (s.vrp.zone === 'DERISK_SHARES') {
    zoneEl.textContent = 'DE-RISK WITH SHARES (insurance rich)'
    zoneEl.className = 'zone-label zone-sell'
  } else if (s.vrp.zone === 'NEUTRAL') {
    zoneEl.textContent = 'NEUTRAL'
    zoneEl.className = 'zone-label zone-neutral'
  } else {
    zoneEl.textContent = '--'
    zoneEl.className = 'zone-label'
  }
}

export function renderEvents(s: Signals): void {
  const container = $('events-rows')
  container.innerHTML = ''
  for (const ev of s.events) {
    const row = document.createElement('div')
    row.className = 'event-row'

    const dateSpan = document.createElement('span')
    dateSpan.textContent = ev.date
    const labelSpan = document.createElement('span')
    labelSpan.textContent = ev.label
    const countdownSpan = document.createElement('span')
    countdownSpan.textContent = ev.days_until >= 0 ? `T-${ev.days_until}d` : 'past'

    row.appendChild(dateSpan)
    row.appendChild(labelSpan)
    row.appendChild(countdownSpan)

    if (ev.in_noadd_window) {
      const badge = document.createElement('span')
      setBadge(badge, 'NO-ADD WINDOW', 'amber')
      row.appendChild(badge)
    }
    container.appendChild(row)
  }
}

export function renderTripwires(s: Signals): void {
  const container = $('tripwire-rows')
  container.innerHTML = ''
  const entries: [string, boolean][] = [
    ['≥2 hyperscaler capex plateau', s.tripwires.hyperscaler_plateau],
    ['Delivered Fed hike', s.tripwires.fed_hike],
    ['TrendForce memory rollover', s.tripwires.memory_rollover],
    ['SOXX 5 consecutive closes < MA200', s.tripwires.ma200_break],
  ]
  for (const [label, tripped] of entries) {
    const row = document.createElement('div')
    row.className = 'tripwire-row'
    const chip = document.createElement('span')
    chip.className = `chip-trigger ${tripped ? 'chip-fail' : 'chip-pass'}`
    chip.textContent = `${tripped ? '✗ TRIPPED' : '✓ OK'} — ${label}`
    row.appendChild(chip)
    container.appendChild(row)
  }
}

export function renderUpstream(s: Signals): void {
  const unavailable = $('upstream-unavailable')
  const body = $('upstream-body')
  if (!s.upstream.available) {
    unavailable.style.display = ''
    body.style.display = 'none'
    return
  }
  unavailable.style.display = 'none'
  body.style.display = ''
  $('upstream-state').textContent = s.upstream.state ?? '--'
  $('upstream-id20').textContent = s.upstream.id20 !== null ? pct(s.upstream.id20) : '--'
  $('upstream-on20').textContent = s.upstream.on20 !== null ? pct(s.upstream.on20) : '--'
  $('upstream-dist20').textContent = s.upstream.dist20 !== null ? String(s.upstream.dist20) : '--'
}

export function renderChecklist(s: Signals): void {
  const container = $('checklist-rows')
  container.innerHTML = ''
  for (const item of s.checklist) {
    const row = document.createElement('div')
    row.className = 'checklist-row'
    const value = item.value === null || item.value === undefined ? '--' : String(item.value)

    const labelSpan = document.createElement('span')
    labelSpan.textContent = item.label
    const valueStrong = document.createElement('strong')
    valueStrong.textContent = value
    row.appendChild(labelSpan)
    row.appendChild(valueStrong)

    if (item.act !== undefined) {
      const badge = document.createElement('span')
      setBadge(badge, item.act ? 'ACT' : 'HOLD', item.act ? 'red' : 'green')
      row.appendChild(badge)
    }
    container.appendChild(row)
  }
}

function volDescription(rv20: number): string {
  if (rv20 <= 0.55) return 'calm'
  if (rv20 <= 0.65) return 'a bit elevated'
  if (rv20 <= 0.90) return 'high'
  return 'extreme'
}

function trendDescription(T: number): string {
  if (T === 1.0) return 'The long-term trend is intact — SOXX is above its 200-day average.'
  if (T === 0.5) {
    return 'The long-term trend has weakened — SOXX dipped below its 200-day average, so ' +
      'exposure is being trimmed as a precaution.'
  }
  return 'The long-term trend has broken down — SOXX has closed below its 200-day average for ' +
    '5+ sessions in a row, so exposure is being cut sharply until it recovers.'
}

export function renderSummary(s: Signals): void {
  const headlineEl = $('summary-headline')
  const actionEl = $('summary-action')
  const whyEl = $('summary-why')
  whyEl.innerHTML = ''

  const targetPct = Math.round(s.engine.e_target * 100)
  const deployedPct = Math.round(s.engine.deployed * 100)
  const gapPct = Math.round(Math.abs(s.engine.gap) * 100)
  const increasing = s.engine.gap > 0

  let headline: string
  let headlineClass: 'summary-headline-hold' | 'summary-headline-act' | 'summary-headline-warn'
  let action: string

  if (s.tripwires.any) {
    headline = 'Pause — the plan needs a review'
    headlineClass = 'summary-headline-warn'
    action = 'A major red-flag condition has been triggered (see the Tripwire Board below). ' +
      "Don't act on today's numbers until the plan has been reviewed against what changed."
  } else if (s.caps.sleeve_breach) {
    headline = 'Stop-loss triggered — move to cash'
    headlineClass = 'summary-headline-warn'
    action = `Your invested position has lost more than the plan allows for (blended ` +
      `${pct(s.caps.sleeve_pnl)}). This rule overrides everything else: reduce to flat.`
  } else if (s.engine.act) {
    headline = increasing
      ? `Move toward ${targetPct}% invested in SOXL`
      : `Reduce toward ${targetPct}% invested in SOXL`
    headlineClass = 'summary-headline-act'
    action = `You're currently at ${deployedPct}% invested; today's target is ${targetPct}%. ` +
      (increasing ? 'Move money into SOXL' : 'Move money out of SOXL') +
      ' at today\'s closing auction (MOC) — never at tomorrow\'s open.'
  } else {
    headline = 'Hold steady — no changes needed today'
    headlineClass = 'summary-headline-hold'
    action = `You're at ${deployedPct}% invested against a ${targetPct}% target. That ` +
      `${gapPct}-point gap is too small to act on (the plan only moves once it reaches 10 ` +
      'points), so there\'s no trade today.'
  }

  headlineEl.textContent = headline
  headlineEl.className = `summary-headline ${headlineClass}`
  actionEl.textContent = action

  const bullets: string[] = [
    `Market volatility is ${volDescription(s.engine.rv20)} right now (${pct(s.engine.rv20)} ` +
      'annualized) — this is the main thing driving how much the plan wants you invested.',
    trendDescription(s.engine.gate.T),
  ]
  if (s.vrp.zone === 'BUY_OPTIONALITY') {
    bullets.push('Options are pricing cheap relative to how much the market is actually moving.')
  } else if (s.vrp.zone === 'DERISK_SHARES') {
    bullets.push('Options are pricing rich relative to realized moves right now.')
  }
  const armed = s.tranches.find((t) => t.status === 'ARMED')
  if (deployedPct === 0 && s.tranches.every((t) => t.status !== 'ARMED')) {
    bullets.push("You're fully in cash. This plan deploys in stages rather than all at once — " +
      'see the Tranche Board below for what has to happen first.')
  } else if (armed) {
    bullets.push(`${armed.id} is armed and ready to deploy — see the Tranche Board below.`)
  }

  for (const b of bullets) {
    const li = document.createElement('li')
    li.textContent = b
    whyEl.appendChild(li)
  }
}

export function renderAll(state: AppState, s: Signals): void {
  renderSummary(s)
  renderHeader(state, s)
  renderGauge(s)
  renderTranches(s)
  renderCaps(s)
  renderVRP(s)
  renderEvents(s)
  renderTripwires(s)
  renderUpstream(s)
  renderChecklist(s)
}
