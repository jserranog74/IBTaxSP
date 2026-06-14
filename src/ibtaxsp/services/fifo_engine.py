from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from ibtaxsp.models import (
    ConversionRateEntry,
    FifoDisposition,
    FifoMatch,
    FifoOpenLot,
    FifoYearResult,
    NormalizedTrade,
    UnsupportedFifoEvent,
    YearDataset,
)


@dataclass
class _Lot:
    symbol: str
    buy_trade_date: str
    buy_date_time: str
    currency: str
    remaining_quantity: float
    unit_cost_usd: float
    unit_cost_eur: float
    transaction_id: str | None
    order_id: str | None
    order_total_quantity: float | None


class _RateBook:
    def __init__(self, datasets: list[YearDataset]) -> None:
        self._rates_by_date: dict[str, dict[tuple[str, str], float]] = {}
        for dataset in datasets:
            for rate in dataset.conversion_rates:
                self._rates_by_date.setdefault(rate.report_date, {})[
                    (rate.from_currency, rate.to_currency)
                ] = rate.rate

    def convert_to_eur(self, amount: float, currency: str, report_date: str) -> float:
        if currency == "EUR":
            return amount
        if currency == "USD":
            return amount / self._get_rate(report_date, "EUR", "USD")

        rate_to_usd = self._get_rate(report_date, currency, "USD")
        eur_to_usd = self._get_rate(report_date, "EUR", "USD")
        return amount * rate_to_usd / eur_to_usd

    def _get_rate(self, report_date: str, from_currency: str, to_currency: str) -> float:
        daily = self._rates_by_date.get(report_date)
        if daily is None:
            raise KeyError(f"Missing rates for date {report_date}")
        try:
            return daily[(from_currency, to_currency)]
        except KeyError as exc:
            raise KeyError(
                f"Missing rate {from_currency}->{to_currency} for {report_date}"
            ) from exc


class FifoEngine:
    def compute(self, datasets: list[YearDataset], target_year: int) -> FifoYearResult:
        ordered_datasets = sorted(datasets, key=lambda item: item.year)
        rate_book = _RateBook(ordered_datasets)
        lots_by_symbol: dict[str, deque[_Lot]] = defaultdict(deque)
        dispositions: list[FifoDisposition] = []
        unsupported_events: list[UnsupportedFifoEvent] = []
        pending_short_closures: dict[str, float] = defaultdict(float)
        order_totals = self._build_order_totals(ordered_datasets)

        self._seed_opening_lots(lots_by_symbol, rate_book, ordered_datasets)

        trades = self._sorted_stock_trades(ordered_datasets)
        for trade in trades:
            if trade.buy_sell == "BUY":
                if pending_short_closures[trade.symbol] > 0:
                    pending_short_closures[trade.symbol] -= abs(trade.quantity)
                    unsupported_events.append(
                        UnsupportedFifoEvent(
                            symbol=trade.symbol,
                            trade_date=trade.trade_date,
                            date_time=trade.date_time,
                            transaction_id=trade.transaction_id,
                            reason="short_cover_not_supported",
                            quantity=abs(trade.quantity),
                            side=trade.buy_sell,
                        )
                    )
                    if pending_short_closures[trade.symbol] <= 1e-12:
                        pending_short_closures.pop(trade.symbol, None)
                    continue
                self._register_buy(lots_by_symbol, rate_book, trade, order_totals)
            elif trade.buy_sell == "SELL":
                try:
                    disposition = self._register_sell(lots_by_symbol, rate_book, trade, order_totals)
                except ValueError:
                    if trade.open_close_indicator == "O":
                        pending_short_closures[trade.symbol] += abs(trade.quantity)
                        unsupported_events.append(
                            UnsupportedFifoEvent(
                                symbol=trade.symbol,
                                trade_date=trade.trade_date,
                                date_time=trade.date_time,
                                transaction_id=trade.transaction_id,
                                reason="short_open_not_supported",
                                quantity=abs(trade.quantity),
                                side=trade.buy_sell,
                            )
                        )
                        continue
                    raise
                if trade.trade_date.startswith(str(target_year)):
                    dispositions.append(disposition)

        open_lots = self._export_open_lots(lots_by_symbol)
        total_gain_usd = sum(item.gain_usd for item in dispositions)
        total_gain_eur = sum(item.gain_eur for item in dispositions)

        return FifoYearResult(
            year=target_year,
            dispositions=dispositions,
            open_lots=open_lots,
            unsupported_events=unsupported_events,
            total_gain_usd=total_gain_usd,
            total_gain_eur=total_gain_eur,
        )

    def _seed_opening_lots(
        self,
        lots_by_symbol: dict[str, deque[_Lot]],
        rate_book: _RateBook,
        datasets: list[YearDataset],
    ) -> None:
        if not datasets:
            return

        for position in datasets[0].year_start_positions:
            if position.kind != "stock_lot" or position.quantity <= 0:
                continue
            if position.cost_basis is None:
                continue

            report_date = position.report_date
            unit_cost_usd = position.cost_basis / position.quantity
            unit_cost_eur = rate_book.convert_to_eur(unit_cost_usd, "USD", report_date)
            lots_by_symbol[position.symbol_or_currency].append(
                _Lot(
                    symbol=position.symbol_or_currency,
                    buy_trade_date=position.open_date_time.split(";")[0]
                    if position.open_date_time
                    else report_date,
                    buy_date_time=position.open_date_time or report_date,
                    currency="USD",
                    remaining_quantity=position.quantity,
                    unit_cost_usd=unit_cost_usd,
                    unit_cost_eur=unit_cost_eur,
                    transaction_id=None,
                    order_id=None,
                    order_total_quantity=position.quantity,
                )
            )

    def _sorted_stock_trades(self, datasets: list[YearDataset]) -> list[NormalizedTrade]:
        trades = [
            trade
            for dataset in datasets
            for trade in dataset.trades
            if trade.asset_category == "STK" and trade.buy_sell in {"BUY", "SELL"}
        ]
        return sorted(
            trades,
            key=lambda item: (item.trade_date, item.date_time, item.transaction_id or ""),
        )

    def _register_buy(
        self,
        lots_by_symbol: dict[str, deque[_Lot]],
        rate_book: _RateBook,
        trade: NormalizedTrade,
        order_totals: dict[tuple[str, str, str | None, str], float],
    ) -> None:
        quantity = abs(trade.quantity)
        unit_cost_usd = trade.cost / quantity
        unit_cost_eur = rate_book.convert_to_eur(unit_cost_usd, trade.currency, trade.report_date)
        lots_by_symbol[trade.symbol].append(
            _Lot(
                symbol=trade.symbol,
                buy_trade_date=trade.trade_date,
                buy_date_time=trade.date_time,
                currency=trade.currency,
                remaining_quantity=quantity,
                unit_cost_usd=unit_cost_usd,
                unit_cost_eur=unit_cost_eur,
                transaction_id=trade.transaction_id,
                order_id=trade.ib_order_id,
                order_total_quantity=order_totals.get(
                    (trade.symbol, trade.trade_date, trade.ib_order_id, trade.buy_sell or "")
                ),
            )
        )

    def _register_sell(
        self,
        lots_by_symbol: dict[str, deque[_Lot]],
        rate_book: _RateBook,
        trade: NormalizedTrade,
        order_totals: dict[tuple[str, str, str | None, str], float],
    ) -> FifoDisposition:
        remaining_to_match = abs(trade.quantity)
        sell_unit_proceeds_usd = trade.net_cash / abs(trade.quantity)
        sell_unit_proceeds_eur = rate_book.convert_to_eur(
            sell_unit_proceeds_usd, trade.currency, trade.report_date
        )

        matches: list[FifoMatch] = []
        total_basis_usd = 0.0
        total_basis_eur = 0.0
        total_proceeds_usd = 0.0
        total_proceeds_eur = 0.0

        symbol_lots = lots_by_symbol[trade.symbol]
        while remaining_to_match > 1e-12:
            if not symbol_lots:
                raise ValueError(f"No hay suficientes lotes FIFO para {trade.symbol}")

            lot = symbol_lots[0]
            matched_quantity = min(remaining_to_match, lot.remaining_quantity)

            buy_basis_usd = matched_quantity * lot.unit_cost_usd
            buy_basis_eur = matched_quantity * lot.unit_cost_eur
            sell_proceeds_usd = matched_quantity * sell_unit_proceeds_usd
            sell_proceeds_eur = matched_quantity * sell_unit_proceeds_eur

            matches.append(
                FifoMatch(
                    symbol=trade.symbol,
                    sell_trade_date=trade.trade_date,
                    sell_date_time=trade.date_time,
                    buy_trade_date=lot.buy_trade_date,
                    buy_date_time=lot.buy_date_time,
                    quantity=matched_quantity,
                    buy_currency=lot.currency,
                    sell_currency=trade.currency,
                    buy_unit_cost=lot.unit_cost_usd,
                    sell_unit_proceeds=sell_unit_proceeds_usd,
                    buy_basis_usd=buy_basis_usd,
                    sell_proceeds_usd=sell_proceeds_usd,
                    gain_usd=sell_proceeds_usd - buy_basis_usd,
                    buy_basis_eur=buy_basis_eur,
                    sell_proceeds_eur=sell_proceeds_eur,
                    gain_eur=sell_proceeds_eur - buy_basis_eur,
                    buy_transaction_id=lot.transaction_id,
                    sell_transaction_id=trade.transaction_id,
                    buy_order_id=lot.order_id,
                    sell_order_id=trade.ib_order_id,
                    buy_order_total_quantity=lot.order_total_quantity,
                    sell_order_total_quantity=order_totals.get(
                        (trade.symbol, trade.trade_date, trade.ib_order_id, trade.buy_sell or "")
                    ),
                )
            )

            total_basis_usd += buy_basis_usd
            total_basis_eur += buy_basis_eur
            total_proceeds_usd += sell_proceeds_usd
            total_proceeds_eur += sell_proceeds_eur

            lot.remaining_quantity -= matched_quantity
            remaining_to_match -= matched_quantity
            if lot.remaining_quantity <= 1e-12:
                symbol_lots.popleft()

        return FifoDisposition(
            symbol=trade.symbol,
            sell_trade_date=trade.trade_date,
            sell_date_time=trade.date_time,
            quantity=abs(trade.quantity),
            sell_trade_price=trade.trade_price,
            proceeds_usd=total_proceeds_usd,
            basis_usd=total_basis_usd,
            gain_usd=total_proceeds_usd - total_basis_usd,
            proceeds_eur=total_proceeds_eur,
            basis_eur=total_basis_eur,
            gain_eur=total_proceeds_eur - total_basis_eur,
            sell_transaction_id=trade.transaction_id,
            sell_order_id=trade.ib_order_id,
            matches=matches,
        )

    def _export_open_lots(
        self, lots_by_symbol: dict[str, deque[_Lot]]
    ) -> list[FifoOpenLot]:
        open_lots: list[FifoOpenLot] = []
        for symbol in sorted(lots_by_symbol):
            for lot in lots_by_symbol[symbol]:
                if lot.remaining_quantity <= 1e-12:
                    continue
                open_lots.append(
                    FifoOpenLot(
                        symbol=symbol,
                        buy_trade_date=lot.buy_trade_date,
                        buy_date_time=lot.buy_date_time,
                        remaining_quantity=lot.remaining_quantity,
                        unit_cost_usd=lot.unit_cost_usd,
                        unit_cost_eur=lot.unit_cost_eur,
                        transaction_id=lot.transaction_id,
                    )
                )
        return open_lots

    def _build_order_totals(
        self, datasets: list[YearDataset]
    ) -> dict[tuple[str, str, str | None, str], float]:
        totals: dict[tuple[str, str, str | None, str], float] = defaultdict(float)
        for trade in self._sorted_stock_trades(datasets):
            key = (trade.symbol, trade.trade_date, trade.ib_order_id, trade.buy_sell or "")
            totals[key] += abs(trade.quantity)
        return dict(totals)
