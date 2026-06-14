from __future__ import annotations

from dataclasses import dataclass

from ibtaxsp.models import AmountSummary, AnnualTaxSummary, UnsupportedFifoEvent, YearDataset
from ibtaxsp.services.i18n import normalize_lang


@dataclass
class _RateBook:
    rates_by_date: dict[str, dict[tuple[str, str], float]]

    @classmethod
    def from_datasets(cls, datasets: list[YearDataset]) -> "_RateBook":
        rates_by_date: dict[str, dict[tuple[str, str], float]] = {}
        for dataset in datasets:
            for rate in dataset.conversion_rates:
                rates_by_date.setdefault(rate.report_date, {})[
                    (rate.from_currency, rate.to_currency)
                ] = rate.rate
        return cls(rates_by_date=rates_by_date)

    def convert_to_eur(self, amount: float, currency: str, report_date: str) -> float:
        if currency == "EUR":
            return amount
        if currency == "USD":
            return amount / self._get_rate(report_date, "EUR", "USD")
        rate_to_usd = self._get_rate(report_date, currency, "USD")
        eur_to_usd = self._get_rate(report_date, "EUR", "USD")
        return amount * rate_to_usd / eur_to_usd

    def convert_to_usd(self, amount: float, currency: str, report_date: str) -> float:
        if currency == "USD":
            return amount
        if currency == "EUR":
            return amount * self._get_rate(report_date, "EUR", "USD")
        return amount * self._get_rate(report_date, currency, "USD")

    def _get_rate(self, report_date: str, from_currency: str, to_currency: str) -> float:
        daily = self.rates_by_date.get(report_date)
        if daily is None:
            raise KeyError(f"Missing rates for date {report_date}")
        try:
            return daily[(from_currency, to_currency)]
        except KeyError as exc:
            raise KeyError(
                f"Missing rate {from_currency}->{to_currency} for {report_date}"
            ) from exc


class AnnualTaxCalculator:
    def build_summary(
        self,
        year: int,
        datasets: list[YearDataset],
        stock_gain_eur: float,
        stock_gain_usd: float,
        fx_gain_eur: float,
        fx_gain_usd: float,
        unsupported_fifo_events: list[UnsupportedFifoEvent],
        lang: str = "es",
    ) -> AnnualTaxSummary:
        lang = normalize_lang(lang)
        rate_book = _RateBook.from_datasets(datasets)
        dataset = next(item for item in datasets if item.year == year)

        dividends = AmountSummary()
        dividend_withholding = AmountSummary()
        interest_received = AmountSummary()
        interest_paid = AmountSummary()
        interest_withholding = AmountSummary()
        deposits = AmountSummary()
        withdrawals = AmountSummary()

        for item in dataset.cash_transactions:
            eur_amount = rate_book.convert_to_eur(item.amount, item.currency, item.report_date)
            usd_amount = rate_book.convert_to_usd(item.amount, item.currency, item.report_date)

            if item.transaction_type == "Dividends":
                dividends.amount_usd += usd_amount
                dividends.amount_eur += eur_amount
            elif item.transaction_type == "Deposits/Withdrawals":
                if item.amount >= 0:
                    deposits.amount_usd += usd_amount
                    deposits.amount_eur += eur_amount
                else:
                    withdrawals.amount_usd += abs(usd_amount)
                    withdrawals.amount_eur += abs(eur_amount)
            elif item.transaction_type == "Broker Interest Received":
                interest_received.amount_usd += usd_amount
                interest_received.amount_eur += eur_amount
            elif item.transaction_type == "Broker Interest Paid":
                interest_paid.amount_usd += abs(usd_amount)
                interest_paid.amount_eur += abs(eur_amount)
            elif item.transaction_type == "Withholding Tax":
                target = (
                    dividend_withholding
                    if "DIVIDEND" in item.description.upper()
                    else interest_withholding
                )
                target.amount_usd += abs(usd_amount)
                target.amount_eur += abs(eur_amount)

        notes = self._notes(lang)

        return AnnualTaxSummary(
            year=year,
            stock_gains=AmountSummary(amount_usd=stock_gain_usd, amount_eur=stock_gain_eur),
            fx_gains=AmountSummary(amount_usd=fx_gain_usd, amount_eur=fx_gain_eur),
            dividends=dividends,
            dividend_withholding=dividend_withholding,
            interest_received=interest_received,
            interest_paid=interest_paid,
            interest_withholding=interest_withholding,
            deposits=deposits,
            withdrawals=withdrawals,
            unsupported_fifo_events=unsupported_fifo_events,
            notes=notes,
        )

    def _notes(self, lang: str) -> list[str]:
        if lang == "en":
            return [
                "Renta-oriented summary: securities gains, FX gains, dividends, interest, and withholdings.",
                "Short sales or unsupported operations are listed separately and excluded from FIFO totals.",
                "A later cash withdrawal does not re-tax the stock sale already reported; it may only create an additional FX effect.",
            ]
        return [
            "Resumen orientado a renta: ganancias de valores, divisa, dividendos, intereses y retenciones.",
            "Las ventas en corto u operativas no soportadas se listan aparte y no se incluyen en el total FIFO.",
            "La retirada posterior de efectivo no vuelve a tributar por la venta ya declarada; solo puede generar efecto fiscal adicional por divisa.",
        ]
