from __future__ import annotations

from collections import defaultdict
import re

from ibtaxsp.models import (
    AnnualTaxSummary,
    DividendEntry,
    RentaView,
    SymbolGainSummary,
    YearDataset,
)
from ibtaxsp.services.annual_tax import _RateBook
from ibtaxsp.models import FifoYearResult


_SYMBOL_RE = re.compile(r"^([A-Z0-9.\-]+)\(")


class RentaViewBuilder:
    def build(
        self,
        year: int,
        dataset: YearDataset,
        annual_summary: AnnualTaxSummary,
        fifo_result: FifoYearResult,
    ) -> RentaView:
        gains_by_symbol = self._build_symbol_gains(fifo_result)
        dividend_entries = self._build_dividend_entries(dataset)

        return RentaView(
            year=year,
            tax_summary=annual_summary,
            gains_by_symbol=gains_by_symbol,
            dividend_entries=dividend_entries,
            disposition_count=len(fifo_result.dispositions),
            fx_event_count=len(dataset.fx_transactions),
        )

    def _build_symbol_gains(self, fifo_result: FifoYearResult) -> list[SymbolGainSummary]:
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
