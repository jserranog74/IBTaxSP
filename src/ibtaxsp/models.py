from __future__ import annotations

from pydantic import BaseModel


class AvailableYear(BaseModel):
    year: int
    xml_path: str


class YearSummary(BaseModel):
    year: int
    statement_count: int
    trade_count: int
    fx_transaction_count: int
    cash_transaction_count: int
    transfer_count: int
    corporate_action_count: int
    first_statement_date: str | None
    last_statement_date: str | None
    base_currency: str | None
    starting_base_cash: float | None
    ending_base_cash: float | None
    ending_cash_by_currency: dict[str, float]
    ending_stock_positions: dict[str, float]
    ending_fx_positions: dict[str, float]


class OverviewResponse(BaseModel):
    years: list[YearSummary]


class NormalizedTrade(BaseModel):
    report_date: str
    date_time: str
    trade_date: str
    settle_date_target: str | None
    asset_category: str
    symbol: str
    description: str
    currency: str
    quantity: float
    trade_price: float
    proceeds: float
    net_cash: float
    commission: float
    taxes: float
    cost: float
    fifo_pnl_realized: float
    mtm_pnl: float
    buy_sell: str | None
    transaction_type: str | None
    open_close_indicator: str | None
    ib_order_id: str | None
    transaction_id: str | None


class NormalizedFxTransaction(BaseModel):
    report_date: str
    date_time: str
    functional_currency: str
    fx_currency: str
    activity_description: str
    quantity: float
    proceeds: float
    cost: float
    realized_pl: float
    code: str | None


class NormalizedCashTransaction(BaseModel):
    report_date: str
    date_time: str
    settle_date: str | None
    available_for_trading_date: str | None
    currency: str
    description: str
    amount: float
    transaction_type: str
    fx_rate_to_base: float | None
    transaction_id: str | None


class NormalizedTransfer(BaseModel):
    report_date: str
    date_time: str
    currency: str | None
    type: str | None
    direction: str | None
    quantity: float | None
    amount: float | None
    description: str | None
    transaction_id: str | None


class PositionSnapshot(BaseModel):
    report_date: str
    asset_category: str
    symbol_or_currency: str
    quantity: float
    cost_basis: float | None
    mark_price: float | None
    value: float | None
    pnl_unrealized: float | None
    kind: str
    open_date_time: str | None = None


class ConversionRateEntry(BaseModel):
    report_date: str
    from_currency: str
    to_currency: str
    rate: float


class YearDataset(BaseModel):
    year: int
    trades: list[NormalizedTrade]
    fx_transactions: list[NormalizedFxTransaction]
    cash_transactions: list[NormalizedCashTransaction]
    transfers: list[NormalizedTransfer]
    year_start_positions: list[PositionSnapshot]
    year_end_positions: list[PositionSnapshot]
    conversion_rates: list[ConversionRateEntry]


class FifoMatch(BaseModel):
    symbol: str
    sell_trade_date: str
    sell_date_time: str
    buy_trade_date: str
    buy_date_time: str
    quantity: float
    buy_currency: str
    sell_currency: str
    buy_unit_cost: float
    sell_unit_proceeds: float
    buy_basis_usd: float
    sell_proceeds_usd: float
    gain_usd: float
    buy_basis_eur: float
    sell_proceeds_eur: float
    gain_eur: float
    buy_transaction_id: str | None
    sell_transaction_id: str | None
    buy_order_id: str | None
    sell_order_id: str | None
    buy_order_total_quantity: float | None
    sell_order_total_quantity: float | None


class FifoDisposition(BaseModel):
    symbol: str
    sell_trade_date: str
    sell_date_time: str
    quantity: float
    sell_trade_price: float
    proceeds_usd: float
    basis_usd: float
    gain_usd: float
    proceeds_eur: float
    basis_eur: float
    gain_eur: float
    sell_transaction_id: str | None
    sell_order_id: str | None
    matches: list[FifoMatch]


class FifoOpenLot(BaseModel):
    symbol: str
    buy_trade_date: str
    buy_date_time: str
    remaining_quantity: float
    unit_cost_usd: float
    unit_cost_eur: float
    transaction_id: str | None


class UnsupportedFifoEvent(BaseModel):
    symbol: str
    trade_date: str
    date_time: str
    transaction_id: str | None
    reason: str
    quantity: float
    side: str | None


class FifoYearResult(BaseModel):
    year: int
    dispositions: list[FifoDisposition]
    open_lots: list[FifoOpenLot]
    unsupported_events: list[UnsupportedFifoEvent]
    total_gain_usd: float
    total_gain_eur: float


class AmountSummary(BaseModel):
    amount_usd: float = 0.0
    amount_eur: float = 0.0


class AnnualTaxSummary(BaseModel):
    year: int
    stock_gains: AmountSummary
    fx_gains: AmountSummary
    dividends: AmountSummary
    dividend_withholding: AmountSummary
    interest_received: AmountSummary
    interest_paid: AmountSummary
    interest_withholding: AmountSummary
    deposits: AmountSummary
    withdrawals: AmountSummary
    unsupported_fifo_events: list[UnsupportedFifoEvent]
    notes: list[str]


class SymbolGainSummary(BaseModel):
    symbol: str
    proceeds_eur: float
    basis_eur: float
    gain_eur: float
    proceeds_usd: float
    basis_usd: float
    gain_usd: float
    disposition_count: int


class DividendEntry(BaseModel):
    report_date: str
    symbol: str | None
    gross_usd: float
    gross_eur: float
    withholding_usd: float
    withholding_eur: float
    description: str


class RentaView(BaseModel):
    year: int
    tax_summary: AnnualTaxSummary
    gains_by_symbol: list[SymbolGainSummary]
    dividend_entries: list[DividendEntry]
    disposition_count: int
    fx_event_count: int


class RentaInputBlock(BaseModel):
    title: str
    description: str
    amount_eur: float
    review_notes: list[str]


class RentaGuidance(BaseModel):
    year: int
    blocks: list[RentaInputBlock]
    action_items: list[str]
    caveats: list[str]


class HaciendaEntry(BaseModel):
    section: str
    concept: str
    amount_eur: float
    source: str
    notes: list[str]


class HaciendaChecklistItem(BaseModel):
    label: str
    status: str
    detail: str


class HaciendaView(BaseModel):
    year: int
    entries: list[HaciendaEntry]
    checklist: list[HaciendaChecklistItem]
    warnings: list[str]


class CashFlowEntry(BaseModel):
    report_date: str
    currency: str
    direction: str
    amount: float
    amount_eur: float
    description: str
    fiscal_treatment: str
    notes: list[str]


class CashFlowView(BaseModel):
    year: int
    deposits: list[CashFlowEntry]
    withdrawals: list[CashFlowEntry]
    guidance: list[str]


class WithdrawalSimulationRequest(BaseModel):
    year: int
    amount: float
    currency: str
    lang: str = "es"


class WithdrawalSimulationResult(BaseModel):
    year: int
    requested_amount: float
    currency: str
    available_amount: float
    feasible: bool
    estimated_fx_component_eur: float
    estimated_cash_movement_eur: float
    notes: list[str]
