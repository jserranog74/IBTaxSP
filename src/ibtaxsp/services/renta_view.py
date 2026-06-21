from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from ibtaxsp.models import (
    AnnualTaxSummary,
    DividendEntry,
    FxFilingEntry,
    RentaView,
    SymbolGainSummary,
    YearDataset,
)
from ibtaxsp.services.annual_tax import _RateBook
from ibtaxsp.models import FifoYearResult


_SYMBOL_RE = re.compile(r"^([A-Z0-9.\-]+)\(")


@dataclass
class _FxLot:
    acquisition_date: str
    quantity: float
    unit_cost_usd: float
    description: str


class RentaViewBuilder:
    def build(
        self,
        year: int,
        datasets: list[YearDataset],
        annual_summary: AnnualTaxSummary,
        fifo_result: FifoYearResult,
    ) -> RentaView:
        dataset = next(item for item in datasets if item.year == year)
        gains_by_symbol = self._build_symbol_gains(fifo_result, dataset)
        dividend_entries = self._build_dividend_entries(dataset)
        fx_filing_entries = self._build_fx_filing_entries(year, datasets)

        return RentaView(
            year=year,
            tax_summary=annual_summary,
            gains_by_symbol=gains_by_symbol,
            dividend_entries=dividend_entries,
            fx_filing_entries=fx_filing_entries,
            disposition_count=len(fifo_result.dispositions),
            fx_event_count=len(dataset.fx_transactions),
        )

    def _build_symbol_gains(self, fifo_result: FifoYearResult, dataset: YearDataset) -> list[SymbolGainSummary]:
        issuer_names = self._build_issuer_names(dataset)
        grouped: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "proceeds_eur": 0.0,
                "basis_eur": 0.0,
                "gain_eur": 0.0,
                "proceeds_usd": 0.0,
                "basis_usd": 0.0,
                "gain_usd": 0.0,
                "disposition_count": 0.0,
            }
        )

        for item in fifo_result.dispositions:
            row = grouped[item.symbol]
            row["proceeds_eur"] += item.proceeds_eur
            row["basis_eur"] += item.basis_eur
            row["gain_eur"] += item.gain_eur
            row["proceeds_usd"] += item.proceeds_usd
            row["basis_usd"] += item.basis_usd
            row["gain_usd"] += item.gain_usd
            row["disposition_count"] += 1

        result = [
            SymbolGainSummary(
                symbol=symbol,
                issuer_name=issuer_names.get(symbol),
                proceeds_eur=values["proceeds_eur"],
                basis_eur=values["basis_eur"],
                gain_eur=values["gain_eur"],
                proceeds_usd=values["proceeds_usd"],
                basis_usd=values["basis_usd"],
                gain_usd=values["gain_usd"],
                disposition_count=int(values["disposition_count"]),
            )
            for symbol, values in grouped.items()
        ]
        return sorted(result, key=lambda item: item.gain_eur, reverse=True)

    def _build_issuer_names(self, dataset: YearDataset) -> dict[str, str]:
        names: dict[str, str] = {}
        for trade in dataset.trades:
            if trade.asset_category != "STK":
                continue
            if trade.symbol and trade.description and trade.symbol not in names:
                names[trade.symbol] = trade.description.title()
        return names

    def _build_dividend_entries(self, dataset: YearDataset) -> list[DividendEntry]:
        rate_book = _RateBook.from_datasets([dataset])

        withholding_by_key: dict[tuple[str, str | None], tuple[float, float]] = {}
        for item in dataset.cash_transactions:
            if item.transaction_type != "Withholding Tax":
                continue
            symbol = self._extract_symbol(item.description)
            key = (item.report_date, symbol)
            usd_amount = rate_book.convert_to_usd(abs(item.amount), item.currency, item.report_date)
            eur_amount = rate_book.convert_to_eur(abs(item.amount), item.currency, item.report_date)
            previous = withholding_by_key.get(key, (0.0, 0.0))
            withholding_by_key[key] = (previous[0] + usd_amount, previous[1] + eur_amount)

        result: list[DividendEntry] = []
        for item in dataset.cash_transactions:
            if item.transaction_type != "Dividends":
                continue
            symbol = self._extract_symbol(item.description)
            key = (item.report_date, symbol)
            withholding_usd, withholding_eur = withholding_by_key.get(key, (0.0, 0.0))
            gross_usd = rate_book.convert_to_usd(item.amount, item.currency, item.report_date)
            gross_eur = rate_book.convert_to_eur(item.amount, item.currency, item.report_date)
            result.append(
                DividendEntry(
                    report_date=item.report_date,
                    symbol=symbol,
                    gross_usd=gross_usd,
                    gross_eur=gross_eur,
                    withholding_usd=withholding_usd,
                    withholding_eur=withholding_eur,
                    description=item.description,
                )
            )

        return sorted(result, key=lambda item: (item.report_date, item.symbol or ""))

    def _extract_symbol(self, description: str) -> str | None:
        match = _SYMBOL_RE.match(description)
        if match:
            return match.group(1)
        return None

    def _build_fx_filing_entries(self, year: int, datasets: list[YearDataset]) -> list[FxFilingEntry]:
        rate_book = _RateBook.from_datasets(datasets)
        lots_by_currency: dict[str, list[_FxLot]] = defaultdict(list)
        entries: list[FxFilingEntry] = []

        transactions = [
            item
            for dataset in sorted(datasets, key=lambda current: current.year)
            for item in dataset.fx_transactions
        ]
        transactions.sort(key=lambda item: (item.date_time or item.report_date, item.report_date))

        for item in transactions:
            code_tokens = {token.strip() for token in (item.code or "").split(";") if token.strip()}
            quantity = abs(item.quantity)
            if quantity <= 0:
                continue

            if item.quantity > 0 and "O" in code_tokens:
                lots_by_currency[item.fx_currency].append(
                    _FxLot(
                        acquisition_date=item.report_date,
                        quantity=quantity,
                        unit_cost_usd=abs(item.proceeds) / quantity,
                        description=item.activity_description,
                    )
                )
                continue

            if item.quantity >= 0 or "C" not in code_tokens:
                continue

            remaining_quantity = quantity
            unit_proceeds_usd = abs(item.proceeds) / quantity if quantity else 0.0
            close_rate = rate_book._get_rate(item.report_date, "EUR", "USD")
            lots = lots_by_currency[item.fx_currency]

            while remaining_quantity > 1e-9 and lots:
                lot = lots[0]
                matched_quantity = min(remaining_quantity, lot.quantity)
                acquisition_value_usd = matched_quantity * lot.unit_cost_usd
                transmission_value_usd = matched_quantity * unit_proceeds_usd
                acquisition_value_eur = acquisition_value_usd / close_rate
                transmission_value_eur = transmission_value_usd / close_rate

                if item.report_date.startswith(str(year)):
                    entries.append(
                        FxFilingEntry(
                            acquisition_date=lot.acquisition_date,
                            transmission_date=item.report_date,
                            currency=item.fx_currency,
                            quantity=matched_quantity,
                            acquisition_value_eur=acquisition_value_eur,
                            transmission_value_eur=transmission_value_eur,
                            gain_eur=transmission_value_eur - acquisition_value_eur,
                            acquisition_value_usd=acquisition_value_usd,
                            transmission_value_usd=transmission_value_usd,
                            gain_usd=transmission_value_usd - acquisition_value_usd,
                            acquisition_description=lot.description,
                            transmission_description=item.activity_description,
                        )
                    )

                lot.quantity -= matched_quantity
                remaining_quantity -= matched_quantity
                if lot.quantity <= 1e-9:
                    lots.pop(0)

        return sorted(entries, key=lambda item: (item.transmission_date, item.acquisition_date))
