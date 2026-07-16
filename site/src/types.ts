export interface Trigger {
  name: string
  pass: boolean
}

export interface Tranche {
  id: string
  status: 'DEPLOYED' | 'ARMED' | 'WAITING' | 'SKIPPED'
  pct: number | null
  triggers: Trigger[]
  pnl: number | null
}

export interface EventEntry {
  date: string
  label: string
  in_noadd_window: boolean
  days_until: number
}

export interface ChecklistItem {
  label: string
  value: number | string | boolean | null
  act?: boolean
}

export interface Alert {
  type: string
  title: string
  body: string
}

export interface Signals {
  last_session: string
  generated_utc: string
  data_stale: boolean
  is_preview: boolean
  market: {
    soxx_close: number
    soxl_close: number
    soxx_ret: number
    soxl_ret: number
  }
  engine: {
    rv20: number
    rv20_p90: number
    rules: { R1: number; R2: number; R3: number; R4: number }
    ensemble: number
    gate: { T: number; consec_below_ma200: number; ma200: number }
    e_target: number
    deployed: number
    gap: number
    act: boolean
  }
  tranches: Tranche[]
  caps: {
    tranche_breaches: string[]
    sleeve_pnl: number | null
    sleeve_breach: boolean
  }
  vrp: {
    iv30: number | null
    iv30_asof: string | null
    stale: boolean
    vrp: number | null
    zone: 'BUY_OPTIONALITY' | 'DERISK_SHARES' | 'NEUTRAL' | null
  }
  tripwires: {
    hyperscaler_plateau: boolean
    fed_hike: boolean
    memory_rollover: boolean
    ma200_break: boolean
    any: boolean
  }
  events: EventEntry[]
  upstream: {
    available: boolean
    state: string | null
    id20: number | null
    on20: number | null
    dist20: number | null
    last_session: string | null
  }
  series: {
    dates: string[]
    soxl_close: (number | null)[]
    rv20: (number | null)[]
    rv20_p90: (number | null)[]
    e_target: (number | null)[]
    equity_engine: (number | null)[]
    equity_bh: (number | null)[]
    tranche_marks: { id: string; date: string }[]
  }
  checklist: ChecklistItem[]
  alerts: Alert[]
}
