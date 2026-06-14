import { startTransition, useEffect, useMemo, useState } from 'react'

type Language = 'es' | 'en'

type YearItem = {
  year: number
  xml_path: string
}

type AmountSummary = {
  amount_usd: number
  amount_eur: number
}

type UnsupportedEvent = {
  symbol: string
  trade_date: string
  date_time: string
  transaction_id: string | null
  reason: string
  quantity: number
  side: string | null
}

type TaxSummary = {
  year: number
  stock_gains: AmountSummary
  fx_gains: AmountSummary
  dividends: AmountSummary
  dividend_withholding: AmountSummary
  interest_received: AmountSummary
  interest_paid: AmountSummary
  interest_withholding: AmountSummary
  deposits: AmountSummary
  withdrawals: AmountSummary
  unsupported_fifo_events: UnsupportedEvent[]
  notes: string[]
}

type SymbolGainSummary = {
  symbol: string
  proceeds_eur: number
  basis_eur: number
  gain_eur: number
  proceeds_usd: number
  basis_usd: number
  gain_usd: number
  disposition_count: number
}

type DividendEntry = {
  report_date: string
  symbol: string | null
  gross_usd: number
  gross_eur: number
  withholding_usd: number
  withholding_eur: number
  description: string
}

type FifoMatch = {
  symbol: string
  sell_trade_date: string
  sell_date_time: string
  buy_trade_date: string
  buy_date_time: string
  quantity: number
  buy_currency: string
  sell_currency: string
  buy_unit_cost: number
  sell_unit_proceeds: number
  buy_basis_usd: number
  sell_proceeds_usd: number
  gain_usd: number
  buy_basis_eur: number
  sell_proceeds_eur: number
  gain_eur: number
  buy_transaction_id: string | null
  sell_transaction_id: string | null
  buy_order_id: string | null
  sell_order_id: string | null
  buy_order_total_quantity: number | null
  sell_order_total_quantity: number | null
}

type FifoDisposition = {
  symbol: string
  sell_trade_date: string
  sell_date_time: string
  quantity: number
  sell_trade_price: number
  proceeds_usd: number
  basis_usd: number
  gain_usd: number
  proceeds_eur: number
  basis_eur: number
  gain_eur: number
  sell_transaction_id: string | null
  sell_order_id: string | null
  matches: FifoMatch[]
}

type FifoOpenLot = {
  symbol: string
  buy_trade_date: string
  buy_date_time: string
  remaining_quantity: number
  unit_cost_usd: number
  unit_cost_eur: number
  transaction_id: string | null
}

type FifoResult = {
  year: number
  dispositions: FifoDisposition[]
  open_lots: FifoOpenLot[]
  unsupported_events: UnsupportedEvent[]
  total_gain_usd: number
  total_gain_eur: number
}

type RentaInputBlock = {
  title: string
  description: string
  amount_eur: number
  review_notes: string[]
}

type RentaGuidance = {
  year: number
  blocks: RentaInputBlock[]
  action_items: string[]
  caveats: string[]
}

type HaciendaEntry = {
  section: string
  concept: string
  amount_eur: number
  source: string
  notes: string[]
}

type HaciendaChecklistItem = {
  label: string
  status: string
  detail: string
}

type HaciendaView = {
  year: number
  entries: HaciendaEntry[]
  checklist: HaciendaChecklistItem[]
  warnings: string[]
}

type CashFlowEntry = {
  report_date: string
  currency: string
  direction: string
  amount: number
  amount_eur: number
  description: string
  fiscal_treatment: string
  notes: string[]
}

type CashFlowView = {
  year: number
  deposits: CashFlowEntry[]
  withdrawals: CashFlowEntry[]
  guidance: string[]
}

type WithdrawalSimulationResult = {
  year: number
  requested_amount: number
  currency: string
  available_amount: number
  feasible: boolean
  estimated_fx_component_eur: number
  estimated_cash_movement_eur: number
  notes: string[]
}

type RentaView = {
  year: number
  tax_summary: TaxSummary
  gains_by_symbol: SymbolGainSummary[]
  dividend_entries: DividendEntry[]
  disposition_count: number
  fx_event_count: number
}

type ActiveSection = 'summary' | 'guidance' | 'fifo' | 'hacienda' | 'cashflow'

const API_BASE = 'http://127.0.0.1:8000'

const copy = {
  es: {
    appName: 'IBTaxSP',
    title: 'Panel fiscal de Interactive Brokers para renta espanola',
    subtitle: 'Resumen anual, cadena FIFO auditable, dividendos con retencion y control de divisa en una sola vista.',
    year: 'Ejercicio',
    language: 'Idioma',
    salesAnalyzed: 'Ventas analizadas',
    fxEvents: 'Eventos FX',
    dividends: 'Dividendos',
    sectionSummary: 'Resumen',
    sectionGuidance: 'Ayuda Renta',
    sectionFifo: 'Informe FIFO',
    sectionHacienda: 'Hacienda',
    sectionCashFlow: 'Cash Flow',
    loadingYears: 'No he podido cargar los anos disponibles',
    loadingView: 'No he podido cargar la vista fiscal',
    unexpectedYears: 'Error inesperado al cargar anos',
    unexpectedView: 'Error inesperado al cargar la vista',
    loadingPanel: 'Cargando vista fiscal...',
    cards: {
      stock: 'Ganancia valores',
      fx: 'Ganancia divisa',
      dividends: 'Dividendos brutos',
      withholding: 'Retencion dividendos',
      interest: 'Intereses cobrados',
      deposits: 'Ingresos aportados',
    },
    gainsBySymbol: 'Ganancias por simbolo',
    gainsBySymbolDesc: 'Agregado anual de transmisiones de valores segun FIFO.',
    fiscalBlock: 'Bloque fiscal',
    fiscalBlockDesc: 'Importes principales para trasladar a la declaracion.',
    detailDividends: 'Dividendos y retenciones',
    detailDividendsDesc: 'Detalle para revisar doble imposicion y soporte documental.',
    reviewAlerts: 'Alertas de revision',
    reviewAlertsDesc: 'Eventos que conviene tratar aparte antes de cerrar el ano.',
    calcNotes: 'Notas del calculo',
    calcNotesDesc: 'Recordatorios practicos para interpretar bien el ejercicio.',
    noIssues: 'Sin incidencias tecnicas abiertas',
    noIssuesDesc: 'No hay eventos FIFO no soportados en este ejercicio.',
    guidanceTitle: 'Ayuda Renta',
    guidanceDesc: 'Bloques practicos para trasladar importes y revisar incidencias antes de presentar.',
    actionsTitle: 'Acciones recomendadas',
    actionsDesc: 'Checklist practico antes de trasladar cifras.',
    caveatsTitle: 'Cautelas',
    caveatsDesc: 'Puntos a revisar antes de dar el ejercicio por cerrado.',
    fifoTitle: 'Informe FIFO anual',
    fifoDesc: 'Detalle de ventas y lotes consumidos para justificar las cifras declaradas.',
    filterSymbol: 'Filtrar por activo',
    all: 'Todos',
    totalGainEur: 'Ganancia total EUR',
    fifoSales: 'Ventas FIFO',
    openLots: 'Lotes abiertos',
    sale: 'Venta',
    units: 'titulos',
    order: 'orden',
    proceeds: 'Proceeds',
    cost: 'Coste',
    sellPriceUsdReal: 'Precio venta USD real',
    sellPriceApprox: 'Precio venta aprox.',
    perShare: 'por titulo',
    originOrder: 'Orden origen',
    totalBuy: 'compra total',
    consumedThisSale: 'Consumido en esta venta',
    sourceBuy: 'Compra origen',
    targetSale: 'Venta destino',
    quantity: 'Cantidad',
    buyPriceUsd: 'Precio compra USD',
    sellPriceUsd: 'Precio venta USD',
    costEur: 'Coste EUR',
    saleEur: 'Venta EUR',
    gainEur: 'Ganancia EUR',
    openLotsTitle: 'Lotes abiertos al cierre',
    openLotsDesc: 'Posiciones remanentes con su coste unitario preparado para ejercicios futuros.',
    haciendaTitle: 'Que poner en Hacienda',
    haciendaDesc: 'Vista operativa para trasladar cifras a la declaracion sin perder el origen del calculo.',
    checklistTitle: 'Checklist',
    checklistDesc: 'Estado rapido antes de presentar.',
    warningsTitle: 'Advertencias',
    warningsDesc: 'Puntos a no perder de vista antes de darlo por cerrado.',
    simulationTitle: 'Simulacion de retiro',
    simulationDesc: 'Prueba retiradas cuando quieras sin alterar el historico real importado desde IB.',
    amountToWithdraw: 'Importe a retirar',
    currency: 'Divisa',
    simulateWithdrawal: 'Simular retiro',
    calculating: 'Calculando...',
    invalidAmount: 'Introduce un importe valido mayor que cero.',
    simulationFailed: 'No he podido calcular la simulacion del retiro.',
    simulationUnexpected: 'Error inesperado al simular el retiro',
    availability: 'Disponibilidad',
    feasible: 'Retiro viable',
    notFeasible: 'Retiro no viable al cierre',
    endingBalance: 'Saldo detectado al cierre del ejercicio en la divisa seleccionada.',
    equivalence: 'Equivalencia',
    estimatedEurOutflow: 'Salida estimada en euros',
    estimatedEurOutflowDesc: 'Conversion orientativa del importe simulado a EUR.',
    fxComponent: 'FX',
    estimatedFxComponent: 'Componente estimado de divisa',
    estimatedFxComponentDesc: 'Referencia orientativa del posible efecto fiscal ligado a la divisa.',
    simulationReading: 'Lectura de la simulacion',
    cashFlowTitle: 'Cash Flow y retiros',
    cashFlowDesc: 'Entradas y salidas de caja con una lectura fiscal simple de lo que implica cada movimiento.',
    inflows: 'Entradas',
    detectedDeposits: 'Depositos detectados',
    detectedDepositsDesc: 'Movimientos de efectivo entrante localizados en el ejercicio.',
    outflows: 'Salidas',
    detectedWithdrawals: 'Retiros detectados',
    detectedWithdrawalsDesc: 'Movimientos de efectivo saliente localizados en el ejercicio.',
    noWithdrawals: 'No hay retiros detectados en este ejercicio.',
    movementReading: 'Lectura fiscal del movimiento',
    movementReadingDesc: 'Como interpretar un retiro o entrada de efectivo desde el punto de vista de caja y divisa.',
    practicalGuide: 'Guia practica',
    practicalGuideDesc: 'Que suele ser mas simple de seguir fiscalmente.',
    deposit: 'Deposito',
    withdrawal: 'Retiro',
    date: 'Fecha',
    amount: 'Importe',
    reading: 'Lectura',
    table: {
      symbol: 'Simbolo',
      gainEur: 'Ganancia EUR',
      proceedsEur: 'Proceeds EUR',
      costEur: 'Coste EUR',
      sales: 'Ventas',
      buyDate: 'Fecha compra',
      qty: 'Cantidad',
      unitCostEur: 'Coste unitario EUR',
      unitCostUsd: 'Coste unitario USD',
    },
  },
  en: {
    appName: 'IBTaxSP',
    title: 'Interactive Brokers tax dashboard for Spanish filing',
    subtitle: 'Annual summary, auditable FIFO chain, dividend withholding, and FX control in one place.',
    year: 'Tax year',
    language: 'Language',
    salesAnalyzed: 'Sales analyzed',
    fxEvents: 'FX events',
    dividends: 'Dividends',
    sectionSummary: 'Summary',
    sectionGuidance: 'Filing Help',
    sectionFifo: 'FIFO Report',
    sectionHacienda: 'Tax Agency',
    sectionCashFlow: 'Cash Flow',
    loadingYears: 'Could not load available years',
    loadingView: 'Could not load the tax view',
    unexpectedYears: 'Unexpected error while loading years',
    unexpectedView: 'Unexpected error while loading the view',
    loadingPanel: 'Loading tax view...',
    cards: {
      stock: 'Stock gains',
      fx: 'FX gains',
      dividends: 'Gross dividends',
      withholding: 'Dividend withholding',
      interest: 'Interest received',
      deposits: 'Cash deposited',
    },
    gainsBySymbol: 'Gains by symbol',
    gainsBySymbolDesc: 'Annual aggregate of security disposals under FIFO.',
    fiscalBlock: 'Tax block',
    fiscalBlockDesc: 'Main figures to move into the tax return.',
    detailDividends: 'Dividends and withholdings',
    detailDividendsDesc: 'Detail to review double taxation and documentary support.',
    reviewAlerts: 'Review alerts',
    reviewAlertsDesc: 'Events worth checking before closing the year.',
    calcNotes: 'Calculation notes',
    calcNotesDesc: 'Practical reminders to interpret the year correctly.',
    noIssues: 'No open technical issues',
    noIssuesDesc: 'There are no unsupported FIFO events in this year.',
    guidanceTitle: 'Filing Help',
    guidanceDesc: 'Practical blocks to move amounts and review issues before filing.',
    actionsTitle: 'Recommended actions',
    actionsDesc: 'Practical checklist before moving figures.',
    caveatsTitle: 'Caveats',
    caveatsDesc: 'Points to review before considering the year closed.',
    fifoTitle: 'Annual FIFO report',
    fifoDesc: 'Detailed sales and consumed lots to justify the reported figures.',
    filterSymbol: 'Filter by asset',
    all: 'All',
    totalGainEur: 'Total gain EUR',
    fifoSales: 'FIFO sales',
    openLots: 'Open lots',
    sale: 'Sale',
    units: 'shares',
    order: 'order',
    proceeds: 'Proceeds',
    cost: 'Cost',
    sellPriceUsdReal: 'Actual sale price USD',
    sellPriceApprox: 'Approx. sale price',
    perShare: 'per share',
    originOrder: 'Source order',
    totalBuy: 'total buy',
    consumedThisSale: 'Consumed in this sale',
    sourceBuy: 'Source buy',
    targetSale: 'Target sale',
    quantity: 'Quantity',
    buyPriceUsd: 'Buy price USD',
    sellPriceUsd: 'Sell price USD',
    costEur: 'Cost EUR',
    saleEur: 'Sale EUR',
    gainEur: 'Gain EUR',
    openLotsTitle: 'Open lots at year end',
    openLotsDesc: 'Remaining positions with unit cost ready for future tax years.',
    haciendaTitle: 'What to enter in the tax return',
    haciendaDesc: 'Operational view to transfer figures without losing the origin of the calculation.',
    checklistTitle: 'Checklist',
    checklistDesc: 'Quick status before filing.',
    warningsTitle: 'Warnings',
    warningsDesc: 'Points to keep in mind before considering it done.',
    simulationTitle: 'Withdrawal simulation',
    simulationDesc: 'Test withdrawals anytime without changing the real history imported from IB.',
    amountToWithdraw: 'Amount to withdraw',
    currency: 'Currency',
    simulateWithdrawal: 'Simulate withdrawal',
    calculating: 'Calculating...',
    invalidAmount: 'Enter a valid amount greater than zero.',
    simulationFailed: 'Could not calculate the withdrawal simulation.',
    simulationUnexpected: 'Unexpected error while simulating the withdrawal',
    availability: 'Availability',
    feasible: 'Feasible withdrawal',
    notFeasible: 'Not feasible at year end',
    endingBalance: 'Detected year-end balance in the selected currency.',
    equivalence: 'Equivalence',
    estimatedEurOutflow: 'Estimated EUR outflow',
    estimatedEurOutflowDesc: 'Indicative conversion of the simulated amount to EUR.',
    fxComponent: 'FX',
    estimatedFxComponent: 'Estimated FX component',
    estimatedFxComponentDesc: 'Indicative reference for the potential tax effect linked to currency.',
    simulationReading: 'Simulation reading',
    cashFlowTitle: 'Cash flow and withdrawals',
    cashFlowDesc: 'Cash inflows and outflows with a simple tax reading of what each movement implies.',
    inflows: 'Inflows',
    detectedDeposits: 'Detected deposits',
    detectedDepositsDesc: 'Incoming cash movements found during the year.',
    outflows: 'Outflows',
    detectedWithdrawals: 'Detected withdrawals',
    detectedWithdrawalsDesc: 'Outgoing cash movements found during the year.',
    noWithdrawals: 'No withdrawals were detected in this year.',
    movementReading: 'Tax reading of the movement',
    movementReadingDesc: 'How to interpret a cash withdrawal or inflow from the perspective of cash and currency.',
    practicalGuide: 'Practical guide',
    practicalGuideDesc: 'What is usually simpler to track for tax purposes.',
    deposit: 'Deposit',
    withdrawal: 'Withdrawal',
    date: 'Date',
    amount: 'Amount',
    reading: 'Reading',
    table: {
      symbol: 'Symbol',
      gainEur: 'Gain EUR',
      proceedsEur: 'Proceeds EUR',
      costEur: 'Cost EUR',
      sales: 'Sales',
      buyDate: 'Buy date',
      qty: 'Quantity',
      unitCostEur: 'Unit cost EUR',
      unitCostUsd: 'Unit cost USD',
    },
  },
} satisfies Record<Language, Record<string, unknown>>

function formatMoney(value: number, currency: 'EUR' | 'USD', language: Language) {
  return new Intl.NumberFormat(language === 'es' ? 'es-ES' : 'en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatDate(raw: string) {
  if (raw.length !== 8) return raw
  return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`
}

function formatNumber(value: number, language: Language) {
  return new Intl.NumberFormat(language === 'es' ? 'es-ES' : 'en-US', {
    maximumFractionDigits: 2,
  }).format(value)
}

function App() {
  const [language, setLanguage] = useState<Language>('es')
  const [years, setYears] = useState<YearItem[]>([])
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [view, setView] = useState<RentaView | null>(null)
  const [guidance, setGuidance] = useState<RentaGuidance | null>(null)
  const [fifo, setFifo] = useState<FifoResult | null>(null)
  const [hacienda, setHacienda] = useState<HaciendaView | null>(null)
  const [cashFlow, setCashFlow] = useState<CashFlowView | null>(null)
  const [withdrawalAmount, setWithdrawalAmount] = useState<string>('10000')
  const [withdrawalCurrency, setWithdrawalCurrency] = useState<string>('USD')
  const [withdrawalSimulation, setWithdrawalSimulation] = useState<WithdrawalSimulationResult | null>(null)
  const [isSimulatingWithdrawal, setIsSimulatingWithdrawal] = useState(false)
  const [simulationError, setSimulationError] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<ActiveSection>('summary')
  const [fifoSymbolFilter, setFifoSymbolFilter] = useState<string>('ALL')
  const [isLoadingYears, setIsLoadingYears] = useState(true)
  const [isLoadingView, setIsLoadingView] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const t = copy[language]

  useEffect(() => {
    let ignore = false

    async function loadYears() {
      setIsLoadingYears(true)
      setError(null)
      try {
        const response = await fetch(`${API_BASE}/api/years`)
        if (!response.ok) {
          throw new Error(t.loadingYears)
        }
        const data: YearItem[] = await response.json()
        if (ignore) return
        setYears(data)
        if (data.length > 0) {
          setSelectedYear((current) => current ?? data[data.length - 1].year)
        }
      } catch (err) {
        if (ignore) return
        setError(err instanceof Error ? err.message : t.unexpectedYears)
      } finally {
        if (!ignore) setIsLoadingYears(false)
      }
    }

    void loadYears()
    return () => {
      ignore = true
    }
  }, [t.loadingYears, t.unexpectedYears])

  useEffect(() => {
    if (selectedYear == null) return

    let ignore = false

    async function loadView() {
      setIsLoadingView(true)
      setError(null)
      try {
        const suffix = `?lang=${language}`
        const [viewResponse, guidanceResponse, fifoResponse, haciendaResponse, cashFlowResponse] = await Promise.all([
          fetch(`${API_BASE}/api/year/${selectedYear}/renta-view${suffix}`),
          fetch(`${API_BASE}/api/year/${selectedYear}/renta-guidance${suffix}`),
          fetch(`${API_BASE}/api/year/${selectedYear}/fifo`),
          fetch(`${API_BASE}/api/year/${selectedYear}/hacienda-view${suffix}`),
          fetch(`${API_BASE}/api/year/${selectedYear}/cash-flow${suffix}`),
        ])
        if (!viewResponse.ok || !guidanceResponse.ok || !fifoResponse.ok || !haciendaResponse.ok || !cashFlowResponse.ok) {
          throw new Error(`${t.loadingView} ${selectedYear}`)
        }
        const [viewData, guidanceData, fifoData, haciendaData]: [
          RentaView,
          RentaGuidance,
          FifoResult,
          HaciendaView,
        ] = await Promise.all([
          viewResponse.json(),
          guidanceResponse.json(),
          fifoResponse.json(),
          haciendaResponse.json(),
        ])
        const cashFlowData: CashFlowView = await cashFlowResponse.json()
        if (ignore) return
        setView(viewData)
        setGuidance(guidanceData)
        setFifo(fifoData)
        setHacienda(haciendaData)
        setCashFlow(cashFlowData)
        setWithdrawalSimulation(null)
        setSimulationError(null)
      } catch (err) {
        if (ignore) return
        setError(err instanceof Error ? err.message : t.unexpectedView)
      } finally {
        if (!ignore) setIsLoadingView(false)
      }
    }

    void loadView()
    return () => {
      ignore = true
    }
  }, [selectedYear, language, t.loadingView, t.unexpectedView])

  const headlineCards = useMemo(() => {
    if (!view) return []
    return [
      { label: t.cards.stock, value: formatMoney(view.tax_summary.stock_gains.amount_eur, 'EUR', language) },
      { label: t.cards.fx, value: formatMoney(view.tax_summary.fx_gains.amount_eur, 'EUR', language) },
      { label: t.cards.dividends, value: formatMoney(view.tax_summary.dividends.amount_eur, 'EUR', language) },
      { label: t.cards.withholding, value: formatMoney(view.tax_summary.dividend_withholding.amount_eur, 'EUR', language) },
      { label: t.cards.interest, value: formatMoney(view.tax_summary.interest_received.amount_eur, 'EUR', language) },
      { label: t.cards.deposits, value: formatMoney(view.tax_summary.deposits.amount_eur, 'EUR', language) },
    ]
  }, [view, t, language])

  const fifoSymbols = useMemo(() => {
    if (!fifo) return []
    return Array.from(new Set(fifo.dispositions.map((item) => item.symbol))).sort()
  }, [fifo])

  const filteredDispositions = useMemo(() => {
    if (!fifo) return []
    if (fifoSymbolFilter === 'ALL') return fifo.dispositions
    return fifo.dispositions.filter((item) => item.symbol === fifoSymbolFilter)
  }, [fifo, fifoSymbolFilter])

  async function handleWithdrawalSimulation() {
    if (selectedYear == null) return

    const parsedAmount = Number(withdrawalAmount)
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setSimulationError(t.invalidAmount)
      setWithdrawalSimulation(null)
      return
    }

    setIsSimulatingWithdrawal(true)
    setSimulationError(null)
    try {
      const response = await fetch(`${API_BASE}/api/simulate/withdrawal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year: selectedYear,
          amount: parsedAmount,
          currency: withdrawalCurrency,
          lang: language,
        }),
      })

      if (!response.ok) {
        throw new Error(t.simulationFailed)
      }

      const data: WithdrawalSimulationResult = await response.json()
      setWithdrawalSimulation(data)
    } catch (err) {
      setSimulationError(err instanceof Error ? err.message : t.simulationUnexpected)
      setWithdrawalSimulation(null)
    } finally {
      setIsSimulatingWithdrawal(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">{t.appName}</p>
          <h1>{t.title}</h1>
          <p className="hero-text">{t.subtitle}</p>
        </div>

        <div className="hero-panel">
          <div className="hero-controls">
            <div>
              <label className="field-label" htmlFor="year">
                {t.year}
              </label>
              <select
                id="year"
                className="year-select"
                value={selectedYear ?? ''}
                disabled={isLoadingYears || years.length === 0}
                onChange={(event) => {
                  const nextYear = Number(event.target.value)
                  startTransition(() => setSelectedYear(nextYear))
                }}
              >
                {years.map((year) => (
                  <option key={year.year} value={year.year}>
                    {year.year}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label" htmlFor="language">
                {t.language}
              </label>
              <select
                id="language"
                className="year-select"
                value={language}
                onChange={(event) => setLanguage(event.target.value as Language)}
              >
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>

          <div className="hero-stats">
            <div>
              <span className="stat-label">{t.salesAnalyzed}</span>
              <strong>{view?.disposition_count ?? 0}</strong>
            </div>
            <div>
              <span className="stat-label">{t.fxEvents}</span>
              <strong>{view?.fx_event_count ?? 0}</strong>
            </div>
            <div>
              <span className="stat-label">{t.dividends}</span>
              <strong>{view?.dividend_entries.length ?? 0}</strong>
            </div>
          </div>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}
      {isLoadingView && !view ? <div className="loading-panel">{t.loadingPanel}</div> : null}

      {view ? (
        <main className="dashboard">
          <section className="section-switcher">
            <button className={activeSection === 'summary' ? 'switch-pill active' : 'switch-pill'} onClick={() => setActiveSection('summary')}>
              {t.sectionSummary}
            </button>
            <button className={activeSection === 'guidance' ? 'switch-pill active' : 'switch-pill'} onClick={() => setActiveSection('guidance')}>
              {t.sectionGuidance}
            </button>
            <button className={activeSection === 'fifo' ? 'switch-pill active' : 'switch-pill'} onClick={() => setActiveSection('fifo')}>
              {t.sectionFifo}
            </button>
            <button className={activeSection === 'hacienda' ? 'switch-pill active' : 'switch-pill'} onClick={() => setActiveSection('hacienda')}>
              {t.sectionHacienda}
            </button>
            <button className={activeSection === 'cashflow' ? 'switch-pill active' : 'switch-pill'} onClick={() => setActiveSection('cashflow')}>
              {t.sectionCashFlow}
            </button>
          </section>

          {activeSection === 'summary' ? (
            <>
              <section className="card-grid">
                {headlineCards.map((card) => (
                  <article key={card.label} className="metric-card">
                    <span>{card.label}</span>
                    <strong>{card.value}</strong>
                  </article>
                ))}
              </section>

              <section className="content-grid">
                <article className="panel panel-wide">
                  <div className="panel-head">
                    <h2>{t.gainsBySymbol}</h2>
                    <p>{t.gainsBySymbolDesc}</p>
                  </div>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{t.table.symbol}</th>
                          <th>{t.table.gainEur}</th>
                          <th>{t.table.proceedsEur}</th>
                          <th>{t.table.costEur}</th>
                          <th>{t.table.sales}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {view.gains_by_symbol.map((row) => (
                          <tr key={row.symbol}>
                            <td>{row.symbol}</td>
                            <td className={row.gain_eur >= 0 ? 'positive' : 'negative'}>{formatMoney(row.gain_eur, 'EUR', language)}</td>
                            <td>{formatMoney(row.proceeds_eur, 'EUR', language)}</td>
                            <td>{formatMoney(row.basis_eur, 'EUR', language)}</td>
                            <td>{row.disposition_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="panel">
                  <div className="panel-head">
                    <h2>{t.fiscalBlock}</h2>
                    <p>{t.fiscalBlockDesc}</p>
                  </div>
                  <dl className="summary-list">
                    <div><dt>{t.cards.stock}</dt><dd>{formatMoney(view.tax_summary.stock_gains.amount_eur, 'EUR', language)}</dd></div>
                    <div><dt>{t.cards.fx}</dt><dd>{formatMoney(view.tax_summary.fx_gains.amount_eur, 'EUR', language)}</dd></div>
                    <div><dt>{t.cards.dividends}</dt><dd>{formatMoney(view.tax_summary.dividends.amount_eur, 'EUR', language)}</dd></div>
                    <div><dt>{t.cards.withholding}</dt><dd>{formatMoney(view.tax_summary.dividend_withholding.amount_eur, 'EUR', language)}</dd></div>
                    <div><dt>{t.cards.interest}</dt><dd>{formatMoney(view.tax_summary.interest_received.amount_eur, 'EUR', language)}</dd></div>
                    <div><dt>{language === 'es' ? 'Intereses pagados' : 'Interest paid'}</dt><dd>{formatMoney(view.tax_summary.interest_paid.amount_eur, 'EUR', language)}</dd></div>
                  </dl>
                </article>

                <article className="panel panel-wide">
                  <div className="panel-head">
                    <h2>{t.detailDividends}</h2>
                    <p>{t.detailDividendsDesc}</p>
                  </div>

                  <div className="dividend-list">
                    {view.dividend_entries.map((entry) => (
                      <div key={`${entry.report_date}-${entry.symbol ?? 'unknown'}`} className="dividend-row">
                        <div>
                          <strong>{entry.symbol ?? 'N/A'}</strong>
                          <p>{entry.description}</p>
                        </div>
                        <div>
                          <span>{t.date}</span>
                          <strong>{formatDate(entry.report_date)}</strong>
                        </div>
                        <div>
                          <span>{t.cards.dividends}</span>
                          <strong>{formatMoney(entry.gross_eur, 'EUR', language)}</strong>
                        </div>
                        <div>
                          <span>{t.cards.withholding}</span>
                          <strong>{formatMoney(entry.withholding_eur, 'EUR', language)}</strong>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>

                <article className="panel">
                  <div className="panel-head">
                    <h2>{t.reviewAlerts}</h2>
                    <p>{t.reviewAlertsDesc}</p>
                  </div>

                  <div className="alert-list">
                    {view.tax_summary.unsupported_fifo_events.length === 0 ? (
                      <div className="alert-card ok">
                        <strong>{t.noIssues}</strong>
                        <p>{t.noIssuesDesc}</p>
                      </div>
                    ) : (
                      view.tax_summary.unsupported_fifo_events.map((event) => (
                        <div key={`${event.transaction_id}-${event.reason}`} className="alert-card">
                          <strong>{event.symbol}</strong>
                          <p>{event.reason} · {event.side} · {event.quantity} · {formatDate(event.trade_date)}</p>
                        </div>
                      ))
                    )}
                  </div>
                </article>

                <article className="panel panel-wide">
                  <div className="panel-head">
                    <h2>{t.calcNotes}</h2>
                    <p>{t.calcNotesDesc}</p>
                  </div>
                  <ul className="note-list">
                    {view.tax_summary.notes.map((note) => <li key={note}>{note}</li>)}
                  </ul>
                </article>
              </section>
            </>
          ) : null}

          {activeSection === 'guidance' && guidance ? (
            <section className="content-grid guidance-grid">
              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.guidanceTitle}</h2>
                  <p>{t.guidanceDesc}</p>
                </div>
                <div className="guidance-grid-cards">
                  {guidance.blocks.map((block) => (
                    <article key={block.title} className="guidance-card">
                      <span className="guidance-kicker">Block</span>
                      <h3>{block.title}</h3>
                      <p>{block.description}</p>
                      <strong>{formatMoney(block.amount_eur, 'EUR', language)}</strong>
                      <ul>
                        {block.review_notes.map((note) => <li key={note}>{note}</li>)}
                      </ul>
                    </article>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h2>{t.actionsTitle}</h2>
                  <p>{t.actionsDesc}</p>
                </div>
                <ul className="note-list">
                  {guidance.action_items.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h2>{t.caveatsTitle}</h2>
                  <p>{t.caveatsDesc}</p>
                </div>
                <ul className="note-list">
                  {guidance.caveats.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </article>
            </section>
          ) : null}

          {activeSection === 'fifo' && fifo ? (
            <section className="content-grid fifo-grid">
              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.fifoTitle}</h2>
                  <p>{t.fifoDesc}</p>
                </div>

                <div className="fifo-toolbar">
                  <label className="field-label" htmlFor="fifo-symbol">{t.filterSymbol}</label>
                  <select id="fifo-symbol" className="year-select fifo-select" value={fifoSymbolFilter} onChange={(event) => setFifoSymbolFilter(event.target.value)}>
                    <option value="ALL">{t.all}</option>
                    {fifoSymbols.map((symbol) => <option key={symbol} value={symbol}>{symbol}</option>)}
                  </select>
                </div>

                <div className="fifo-summary-bar">
                  <div>
                    <span>{t.totalGainEur}</span>
                    <strong>{formatMoney(filteredDispositions.reduce((sum, item) => sum + item.gain_eur, 0), 'EUR', language)}</strong>
                  </div>
                  <div>
                    <span>{t.fifoSales}</span>
                    <strong>{filteredDispositions.length}</strong>
                  </div>
                  <div>
                    <span>{t.openLots}</span>
                    <strong>{fifo.open_lots.length}</strong>
                  </div>
                </div>

                <div className="fifo-list">
                  {filteredDispositions.map((item) => (
                    <article key={item.sell_transaction_id ?? `${item.symbol}-${item.sell_date_time}`} className="fifo-card">
                      <div className="fifo-card-head">
                        <div>
                          <strong>{item.symbol}</strong>
                          <p>{t.sale} {formatDate(item.sell_trade_date)} · {item.quantity} {t.units} · {t.order} {item.sell_order_id ?? 'N/D'}</p>
                        </div>
                        <div className={item.gain_eur >= 0 ? 'positive fifo-gain' : 'negative fifo-gain'}>
                          {formatMoney(item.gain_eur, 'EUR', language)}
                        </div>
                      </div>

                      <div className="fifo-meta">
                        <span>{t.proceeds}: {formatMoney(item.proceeds_eur, 'EUR', language)}</span>
                        <span>{t.cost}: {formatMoney(item.basis_eur, 'EUR', language)}</span>
                        <span>{t.sellPriceUsdReal}: {formatMoney(item.sell_trade_price, 'USD', language)} {t.perShare}</span>
                        <span>{t.sellPriceApprox}: {formatMoney(item.proceeds_eur / item.quantity, 'EUR', language)} {t.perShare}</span>
                      </div>

                      <div className="fifo-match-list">
                        {groupMatchesByOrder(item.matches).map((group) => (
                          <div key={group.key} className="fifo-group">
                            <div className="fifo-group-head">
                              <strong>{t.originOrder} {group.orderId ?? 'N/D'} · {formatDate(group.buyTradeDate)} · {t.totalBuy} {group.buyOrderTotalQuantity ?? group.groupQuantity}</strong>
                              <span>{t.consumedThisSale}: {group.groupQuantity}</span>
                            </div>

                            {group.matches.map((match) => (
                              <div key={`${match.buy_transaction_id ?? match.buy_date_time}-${match.sell_transaction_id ?? match.sell_date_time}-${match.quantity}`} className="fifo-match">
                                <div><span>{t.sourceBuy}</span><strong>{formatDate(match.buy_trade_date)}</strong></div>
                                <div><span>{t.targetSale}</span><strong>{formatDate(match.sell_trade_date)}</strong></div>
                                <div><span>{t.quantity}</span><strong>{match.quantity}</strong></div>
                                <div><span>{t.buyPriceUsd}</span><strong>{formatMoney(match.buy_unit_cost, 'USD', language)}</strong></div>
                                <div><span>{t.sellPriceUsd}</span><strong>{formatMoney(match.sell_unit_proceeds, 'USD', language)}</strong></div>
                                <div><span>{t.costEur}</span><strong>{formatMoney(match.buy_basis_eur, 'EUR', language)}</strong></div>
                                <div><span>{t.saleEur}</span><strong>{formatMoney(match.sell_proceeds_eur, 'EUR', language)}</strong></div>
                                <div><span>{t.gainEur}</span><strong className={match.gain_eur >= 0 ? 'positive' : 'negative'}>{formatMoney(match.gain_eur, 'EUR', language)}</strong></div>
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </article>

              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.openLotsTitle}</h2>
                  <p>{t.openLotsDesc}</p>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>{t.table.symbol}</th>
                        <th>{t.table.buyDate}</th>
                        <th>{t.table.qty}</th>
                        <th>{t.table.unitCostEur}</th>
                        <th>{t.table.unitCostUsd}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {fifo.open_lots.map((lot) => (
                        <tr key={`${lot.symbol}-${lot.buy_date_time}-${lot.transaction_id ?? 'seed'}`}>
                          <td>{lot.symbol}</td>
                          <td>{formatDate(lot.buy_trade_date)}</td>
                          <td>{lot.remaining_quantity}</td>
                          <td>{formatMoney(lot.unit_cost_eur, 'EUR', language)}</td>
                          <td>{formatMoney(lot.unit_cost_usd, 'USD', language)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            </section>
          ) : null}

          {activeSection === 'hacienda' && hacienda ? (
            <section className="content-grid guidance-grid">
              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.haciendaTitle}</h2>
                  <p>{t.haciendaDesc}</p>
                </div>
                <div className="guidance-grid-cards">
                  {hacienda.entries.map((entry) => (
                    <article key={`${entry.section}-${entry.concept}`} className="guidance-card">
                      <span className="guidance-kicker">{entry.section}</span>
                      <h3>{entry.concept}</h3>
                      <p>{entry.source}</p>
                      <strong>{formatMoney(entry.amount_eur, 'EUR', language)}</strong>
                      <ul>
                        {entry.notes.map((note) => <li key={note}>{note}</li>)}
                      </ul>
                    </article>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h2>{t.checklistTitle}</h2>
                  <p>{t.checklistDesc}</p>
                </div>
                <div className="alert-list">
                  {hacienda.checklist.map((item) => (
                    <div key={item.label} className={item.status === 'ok' ? 'alert-card ok' : 'alert-card'}>
                      <strong>{item.label}</strong>
                      <p>{item.detail}</p>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h2>{t.warningsTitle}</h2>
                  <p>{t.warningsDesc}</p>
                </div>
                <ul className="note-list">
                  {hacienda.warnings.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </article>
            </section>
          ) : null}

          {activeSection === 'cashflow' && cashFlow ? (
            <section className="content-grid guidance-grid">
              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.simulationTitle}</h2>
                  <p>{t.simulationDesc}</p>
                </div>

                <div className="simulation-panel">
                  <div className="simulation-form">
                    <div>
                      <label className="field-label" htmlFor="withdrawal-amount">{t.amountToWithdraw}</label>
                      <input id="withdrawal-amount" className="text-input" type="number" min="0" step="0.01" value={withdrawalAmount} onChange={(event) => setWithdrawalAmount(event.target.value)} />
                    </div>

                    <div>
                      <label className="field-label" htmlFor="withdrawal-currency">{t.currency}</label>
                      <select id="withdrawal-currency" className="year-select" value={withdrawalCurrency} onChange={(event) => setWithdrawalCurrency(event.target.value)}>
                        <option value="USD">USD</option>
                        <option value="EUR">EUR</option>
                      </select>
                    </div>

                    <div className="simulation-action">
                      <button className="simulate-button" type="button" disabled={isSimulatingWithdrawal} onClick={() => void handleWithdrawalSimulation()}>
                        {isSimulatingWithdrawal ? t.calculating : t.simulateWithdrawal}
                      </button>
                    </div>
                  </div>

                  {simulationError ? <div className="error-banner simulation-error">{simulationError}</div> : null}

                  {withdrawalSimulation ? (
                    <div className="simulation-result-grid">
                      <article className="guidance-card">
                        <span className="guidance-kicker">{t.availability}</span>
                        <h3>{withdrawalSimulation.feasible ? t.feasible : t.notFeasible}</h3>
                        <p>{t.endingBalance}</p>
                        <strong>{formatNumber(withdrawalSimulation.available_amount, language)} {withdrawalSimulation.currency}</strong>
                      </article>

                      <article className="guidance-card">
                        <span className="guidance-kicker">{t.equivalence}</span>
                        <h3>{t.estimatedEurOutflow}</h3>
                        <p>{t.estimatedEurOutflowDesc}</p>
                        <strong>{formatMoney(withdrawalSimulation.estimated_cash_movement_eur, 'EUR', language)}</strong>
                      </article>

                      <article className="guidance-card">
                        <span className="guidance-kicker">{t.fxComponent}</span>
                        <h3>{t.estimatedFxComponent}</h3>
                        <p>{t.estimatedFxComponentDesc}</p>
                        <strong>{formatMoney(withdrawalSimulation.estimated_fx_component_eur, 'EUR', language)}</strong>
                      </article>
                    </div>
                  ) : null}

                  {withdrawalSimulation ? (
                    <div className="simulation-notes">
                      <h3>{t.simulationReading}</h3>
                      <ul className="note-list">
                        {withdrawalSimulation.notes.map((note) => <li key={note}>{note}</li>)}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </article>

              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.cashFlowTitle}</h2>
                  <p>{t.cashFlowDesc}</p>
                </div>
                <div className="guidance-grid-cards">
                  <article className="guidance-card">
                    <span className="guidance-kicker">{t.inflows}</span>
                    <h3>{t.detectedDeposits}</h3>
                    <p>{t.detectedDepositsDesc}</p>
                    <strong>{cashFlow.deposits.length}</strong>
                    <ul>
                      {cashFlow.deposits.map((entry) => (
                        <li key={`${entry.report_date}-${entry.amount}-${entry.currency}`}>
                          {formatDate(entry.report_date)} · {formatNumber(entry.amount, language)} {entry.currency} · {formatMoney(entry.amount_eur, 'EUR', language)}
                        </li>
                      ))}
                    </ul>
                  </article>

                  <article className="guidance-card">
                    <span className="guidance-kicker">{t.outflows}</span>
                    <h3>{t.detectedWithdrawals}</h3>
                    <p>{t.detectedWithdrawalsDesc}</p>
                    <strong>{cashFlow.withdrawals.length}</strong>
                    <ul>
                      {cashFlow.withdrawals.length === 0 ? (
                        <li>{t.noWithdrawals}</li>
                      ) : (
                        cashFlow.withdrawals.map((entry) => (
                          <li key={`${entry.report_date}-${entry.amount}-${entry.currency}`}>
                            {formatDate(entry.report_date)} · {formatNumber(entry.amount, language)} {entry.currency} · {formatMoney(entry.amount_eur, 'EUR', language)}
                          </li>
                        ))
                      )}
                    </ul>
                  </article>
                </div>
              </article>

              <article className="panel panel-wide">
                <div className="panel-head">
                  <h2>{t.movementReading}</h2>
                  <p>{t.movementReadingDesc}</p>
                </div>
                <div className="dividend-list">
                  {[...cashFlow.deposits, ...cashFlow.withdrawals].map((entry) => (
                    <div key={`${entry.report_date}-${entry.direction}-${entry.amount}-${entry.currency}`} className="dividend-row">
                      <div>
                        <strong>{entry.direction === 'deposit' ? t.deposit : t.withdrawal}</strong>
                        <p>{entry.description}</p>
                      </div>
                      <div>
                        <span>{t.date}</span>
                        <strong>{formatDate(entry.report_date)}</strong>
                      </div>
                      <div>
                        <span>{t.amount}</span>
                        <strong>{formatNumber(entry.amount, language)} {entry.currency}</strong>
                      </div>
                      <div>
                        <span>{t.reading}</span>
                        <strong>{entry.fiscal_treatment}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h2>{t.practicalGuide}</h2>
                  <p>{t.practicalGuideDesc}</p>
                </div>
                <ul className="note-list">
                  {cashFlow.guidance.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </article>
            </section>
          ) : null}
        </main>
      ) : null}
    </div>
  )
}

export default App

function groupMatchesByOrder(matches: FifoMatch[]) {
  const groups: Array<{
    key: string
    orderId: string | null
    buyTradeDate: string
    buyOrderTotalQuantity: number | null
    groupQuantity: number
    matches: FifoMatch[]
  }> = []

  for (const match of matches) {
    const key = `${match.buy_order_id ?? 'NONE'}-${match.buy_trade_date}`
    const current = groups.at(-1)
    if (current && current.key === key) {
      current.matches.push(match)
      current.groupQuantity += match.quantity
      continue
    }
    groups.push({
      key,
      orderId: match.buy_order_id,
      buyTradeDate: match.buy_trade_date,
      buyOrderTotalQuantity: match.buy_order_total_quantity,
      groupQuantity: match.quantity,
      matches: [match],
    })
  }

  return groups
}
