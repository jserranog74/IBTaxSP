from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from ibtaxsp.models import (
    ConversionRateEntry,
    FifoDisposition,
    FifoMatch,
    FifoOpenLot,
    FifoYearResult,
    NormalizedCashTransaction,
    NormalizedFxTransaction,
    NormalizedTrade,
    NormalizedTransfer,
    PositionSnapshot,
    YearDataset,
    YearSummary,
)


@dataclass
class _SummaryAccumulator:
    year: int
    statement_count: int = 0
    trade_count: int = 0
    fx_transaction_count: int = 0
    cash_transaction_count: int = 0
    transfer_count: int = 0
    corporate_action_count: int = 0
    first_statement_date: str | None = None
    last_statement_date: str | None = None
    base_currency: str | None = None
    starting_base_cash: float | None = None
    ending_base_cash: float | None = None
    ending_cash_by_currency: dict[str, float] = field(default_factory=dict)
    ending_stock_positions: Counter[str] = field(default_factory=Counter)
    ending_fx_positions: dict[str, float] = field(default_factory=dict)

    def to_model(self) -> YearSummary:
        return YearSummary(
            year=self.year,
            statement_count=self.statement_count,
            trade_count=self.trade_count,
            fx_transaction_count=self.fx_transaction_count,
            cash_transaction_count=self.cash_transaction_count,
            transfer_count=self.transfer_count,
            corporate_action_count=self.corporate_action_count,
            first_statement_date=self.first_statement_date,
            last_statement_date=self.last_statement_date,
            base_currency=self.base_currency,
            starting_base_cash=self.starting_base_cash,
            ending_base_cash=self.ending_base_cash,
            ending_cash_by_currency=dict(sorted(self.ending_cash_by_currency.items())),
            ending_stock_positions=dict(sorted(self.ending_stock_positions.items())),
            ending_fx_positions=dict(sorted(self.ending_fx_positions.items())),
        )


def _float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


class FlexYearParser:
    def parse_year_summary(self, year: int, xml_path: Path) -> YearSummary:
        root = ET.parse(xml_path).getroot()
        accumulator = _SummaryAccumulator(year=year)

        statements = root.find("FlexStatements")
        if statements is None:
            return accumulator.to_model()

        for statement in statements.findall("FlexStatement"):
            accumulator.statement_count += 1

            from_date = statement.attrib.get("fromDate")
            to_date = statement.attrib.get("toDate")
            if accumulator.first_statement_date is None:
                accumulator.first_statement_date = from_date
            accumulator.last_statement_date = to_date

            self._consume_cash_report(statement, accumulator)
            self._consume_positions(statement, accumulator)
            self._consume_counts(statement, accumulator)

        return accumulator.to_model()

    def parse_year_dataset(self, year: int, xml_path: Path) -> YearDataset:
        root = ET.parse(xml_path).getroot()
        statements = root.find("FlexStatements")

        trades: list[NormalizedTrade] = []
        fx_transactions: list[NormalizedFxTransaction] = []
        cash_transactions: list[NormalizedCashTransaction] = []
        transfers: list[NormalizedTransfer] = []
        year_start_positions: list[PositionSnapshot] = []
        year_end_positions: list[PositionSnapshot] = []
        conversion_rates: list[ConversionRateEntry] = []

        if statements is None:
            return YearDataset(
                year=year,
                trades=trades,
                fx_transactions=fx_transactions,
                cash_transactions=cash_transactions,
                transfers=transfers,
                year_end_positions=year_end_positions,
            )

        first_statement: ET.Element | None = None
        last_statement: ET.Element | None = None
        for statement in statements.findall("FlexStatement"):
            if first_statement is None:
                first_statement = statement
            last_statement = statement
            trades.extend(self._parse_trades(statement))
            fx_transactions.extend(self._parse_fx_transactions(statement))
            cash_transactions.extend(self._parse_cash_transactions(statement))
            transfers.extend(self._parse_transfers(statement))
            conversion_rates.extend(self._parse_conversion_rates(statement))

        if first_statement is not None:
            year_start_positions = self._parse_position_snapshots(first_statement)
        if last_statement is not None:
            year_end_positions = self._parse_position_snapshots(last_statement)

        return YearDataset(
            year=year,
            trades=trades,
            fx_transactions=fx_transactions,
            cash_transactions=cash_transactions,
            transfers=transfers,
            year_start_positions=year_start_positions,
            year_end_positions=year_end_positions,
            conversion_rates=conversion_rates,
        )

    def _consume_cash_report(
        self, statement: ET.Element, accumulator: _SummaryAccumulator
    ) -> None:
        cash_report = statement.find("CashReport")
        if cash_report is None:
            return

        base_currency_guess = self._infer_base_currency(statement)
        for currency_line in cash_report.findall("CashReportCurrency"):
            currency = currency_line.attrib.get("currency")
            level = currency_line.attrib.get("levelOfDetail")
            ending_cash = _float(currency_line.attrib.get("endingCash"))
            starting_cash = _float(currency_line.attrib.get("startingCash"))

            if level == "BaseCurrency":
                accumulator.base_currency = base_currency_guess or currency
                if accumulator.starting_base_cash is None:
                    accumulator.starting_base_cash = starting_cash
                accumulator.ending_base_cash = ending_cash
                continue

            if level == "Currency" and currency and ending_cash is not None:
                accumulator.ending_cash_by_currency[currency] = ending_cash

    def _consume_positions(
        self, statement: ET.Element, accumulator: _SummaryAccumulator
    ) -> None:
        open_positions = statement.find("OpenPositions")
        if open_positions is not None:
            accumulator.ending_stock_positions.clear()
            for position in open_positions.findall("OpenPosition"):
                if position.attrib.get("levelOfDetail") != "SUMMARY":
                    continue
                symbol = position.attrib.get("symbol")
                quantity = _float(position.attrib.get("position"))
                if symbol and quantity is not None:
                    accumulator.ending_stock_positions[symbol] = quantity

        fx_positions = statement.find("FxPositions")
        if fx_positions is None:
            accumulator.ending_fx_positions = {}
            return

        summary_positions: dict[str, float] = {}
        for position in fx_positions.findall("FxPosition"):
            if position.attrib.get("levelOfDetail") != "SUMMARY":
                continue
            currency = position.attrib.get("fxCurrency")
            quantity = _float(position.attrib.get("quantity"))
            if currency and quantity is not None:
                summary_positions[currency] = quantity
        accumulator.ending_fx_positions = summary_positions

    def _consume_counts(
        self, statement: ET.Element, accumulator: _SummaryAccumulator
    ) -> None:
        trades = statement.find("Trades")
        if trades is not None:
            accumulator.trade_count += len(trades.findall("Trade"))

        fx_transactions = statement.find("FxTransactions")
        if fx_transactions is not None:
            accumulator.fx_transaction_count += len(fx_transactions.findall("FxTransaction"))

        cash_transactions = statement.find("CashTransactions")
        if cash_transactions is not None:
            accumulator.cash_transaction_count += len(
                cash_transactions.findall("CashTransaction")
            )

        transfers = statement.find("Transfers")
        if transfers is not None:
            accumulator.transfer_count += len(transfers.findall("Transfer"))

        corporate_actions = statement.find("CorporateActions")
        if corporate_actions is not None:
            accumulator.corporate_action_count += len(
                corporate_actions.findall("CorporateAction")
            )

    def _infer_base_currency(self, statement: ET.Element) -> str | None:
        stmt_funds = statement.find("StmtFunds")
        if stmt_funds is None:
            return None

        for line in stmt_funds.findall("StatementOfFundsLine"):
            if line.attrib.get("levelOfDetail") != "Currency":
                continue
            if line.attrib.get("fxRateToBase") == "1":
                currency = line.attrib.get("currency")
                if currency:
                    return currency
        return None

    def _parse_trades(self, statement: ET.Element) -> list[NormalizedTrade]:
        trades_node = statement.find("Trades")
        if trades_node is None:
            return []

        trades: list[NormalizedTrade] = []
        for trade in trades_node.findall("Trade"):
            trades.append(
                NormalizedTrade(
                    report_date=trade.attrib.get("reportDate", ""),
                    date_time=trade.attrib.get("dateTime", ""),
                    trade_date=trade.attrib.get("tradeDate", ""),
                    settle_date_target=trade.attrib.get("settleDateTarget"),
                    asset_category=trade.attrib.get("assetCategory", ""),
                    symbol=trade.attrib.get("symbol", ""),
                    description=trade.attrib.get("description", ""),
                    currency=trade.attrib.get("currency", ""),
                    quantity=float(trade.attrib.get("quantity", "0")),
                    trade_price=float(trade.attrib.get("tradePrice", "0")),
                    proceeds=float(trade.attrib.get("proceeds", "0")),
                    net_cash=float(trade.attrib.get("netCash", "0")),
                    commission=float(trade.attrib.get("ibCommission", "0")),
                    taxes=float(trade.attrib.get("taxes", "0")),
                    cost=float(trade.attrib.get("cost", "0")),
                    fifo_pnl_realized=float(trade.attrib.get("fifoPnlRealized", "0")),
                    mtm_pnl=float(trade.attrib.get("mtmPnl", "0")),
                    buy_sell=trade.attrib.get("buySell"),
                    transaction_type=trade.attrib.get("transactionType"),
                    open_close_indicator=trade.attrib.get("openCloseIndicator"),
                    ib_order_id=trade.attrib.get("ibOrderID"),
                    transaction_id=trade.attrib.get("transactionID"),
                )
            )
        return trades

    def _parse_fx_transactions(
        self, statement: ET.Element
    ) -> list[NormalizedFxTransaction]:
        node = statement.find("FxTransactions")
        if node is None:
            return []

        items: list[NormalizedFxTransaction] = []
        for item in node.findall("FxTransaction"):
            items.append(
                NormalizedFxTransaction(
                    report_date=item.attrib.get("reportDate", ""),
                    date_time=item.attrib.get("dateTime", ""),
                    functional_currency=item.attrib.get("functionalCurrency", ""),
                    fx_currency=item.attrib.get("fxCurrency", ""),
                    activity_description=item.attrib.get("activityDescription", ""),
                    quantity=float(item.attrib.get("quantity", "0")),
                    proceeds=float(item.attrib.get("proceeds", "0")),
                    cost=float(item.attrib.get("cost", "0")),
                    realized_pl=float(item.attrib.get("realizedPL", "0")),
                    code=item.attrib.get("code"),
                )
            )
        return items

    def _parse_cash_transactions(
        self, statement: ET.Element
    ) -> list[NormalizedCashTransaction]:
        node = statement.find("CashTransactions")
        if node is None:
            return []

        items: list[NormalizedCashTransaction] = []
        for item in node.findall("CashTransaction"):
            items.append(
                NormalizedCashTransaction(
                    report_date=item.attrib.get("reportDate", ""),
                    date_time=item.attrib.get("dateTime", ""),
                    settle_date=item.attrib.get("settleDate"),
                    available_for_trading_date=item.attrib.get("availableForTradingDate"),
                    currency=item.attrib.get("currency", ""),
                    description=item.attrib.get("description", ""),
                    amount=float(item.attrib.get("amount", "0")),
                    transaction_type=item.attrib.get("type", ""),
                    fx_rate_to_base=_float(item.attrib.get("fxRateToBase")),
                    transaction_id=item.attrib.get("transactionID"),
                )
            )
        return items

    def _parse_transfers(self, statement: ET.Element) -> list[NormalizedTransfer]:
        node = statement.find("Transfers")
        if node is None:
            return []

        items: list[NormalizedTransfer] = []
        for item in node.findall("Transfer"):
            items.append(
                NormalizedTransfer(
                    report_date=item.attrib.get("reportDate", ""),
                    date_time=item.attrib.get("dateTime", ""),
                    currency=item.attrib.get("currency"),
                    type=item.attrib.get("type"),
                    direction=item.attrib.get("direction"),
                    quantity=_float(item.attrib.get("quantity")),
                    amount=_float(item.attrib.get("amount")),
                    description=item.attrib.get("description"),
                    transaction_id=item.attrib.get("transactionID"),
                )
            )
        return items

    def _parse_position_snapshots(self, statement: ET.Element) -> list[PositionSnapshot]:
        positions: list[PositionSnapshot] = []

        open_positions = statement.find("OpenPositions")
        if open_positions is not None:
            for item in open_positions.findall("OpenPosition"):
                if item.attrib.get("levelOfDetail") != "LOT":
                    continue
                positions.append(
                    PositionSnapshot(
                        report_date=item.attrib.get("reportDate", ""),
                        asset_category=item.attrib.get("assetCategory", ""),
                        symbol_or_currency=item.attrib.get("symbol", ""),
                        quantity=float(item.attrib.get("position", "0")),
                        cost_basis=_float(item.attrib.get("costBasisMoney")),
                        mark_price=_float(item.attrib.get("markPrice")),
                        value=_float(item.attrib.get("positionValue")),
                        pnl_unrealized=_float(item.attrib.get("fifoPnlUnrealized")),
                        kind="stock_lot",
                        open_date_time=item.attrib.get("openDateTime"),
                    )
                )

        fx_positions = statement.find("FxPositions")
        if fx_positions is not None:
            for item in fx_positions.findall("FxLot"):
                positions.append(
                    PositionSnapshot(
                        report_date=item.attrib.get("reportDate", ""),
                        asset_category=item.attrib.get("assetCategory", ""),
                        symbol_or_currency=item.attrib.get("fxCurrency", ""),
                        quantity=float(item.attrib.get("quantity", "0")),
                        cost_basis=_float(item.attrib.get("costBasis")),
                        mark_price=_float(item.attrib.get("closePrice")),
                        value=_float(item.attrib.get("value")),
                        pnl_unrealized=_float(item.attrib.get("unrealizedPL")),
                        kind="fx_lot",
                        open_date_time=item.attrib.get("lotOpenDateTime"),
                    )
                )

        return positions

    def _parse_conversion_rates(self, statement: ET.Element) -> list[ConversionRateEntry]:
        node = statement.find("ConversionRates")
        if node is None:
            return []

        items: list[ConversionRateEntry] = []
        for item in node.findall("ConversionRate"):
            rate = _float(item.attrib.get("rate"))
            if rate is None or rate <= 0:
                continue
            items.append(
                ConversionRateEntry(
                    report_date=item.attrib.get("reportDate", ""),
                    from_currency=item.attrib.get("fromCurrency", ""),
                    to_currency=item.attrib.get("toCurrency", ""),
                    rate=rate,
                )
            )
        return items
