from __future__ import annotations

from ibtaxsp.models import CashFlowEntry, CashFlowView, YearDataset
from ibtaxsp.services.annual_tax import _RateBook
from ibtaxsp.services.i18n import normalize_lang


class CashFlowViewBuilder:
    def build(self, dataset: YearDataset, lang: str = "es") -> CashFlowView:
        lang = normalize_lang(lang)
        rate_book = _RateBook.from_datasets([dataset])
        deposits: list[CashFlowEntry] = []
        withdrawals: list[CashFlowEntry] = []

        for item in dataset.cash_transactions:
            if item.transaction_type != "Deposits/Withdrawals":
                continue

            amount_eur = rate_book.convert_to_eur(item.amount, item.currency, item.report_date)
            direction = "deposit" if item.amount >= 0 else "withdrawal"
            entry = CashFlowEntry(
                report_date=item.report_date,
                currency=item.currency,
                direction=direction,
                amount=abs(item.amount),
                amount_eur=abs(amount_eur),
                description=item.description,
                fiscal_treatment=self._fiscal_treatment(item.currency, direction, lang),
                notes=self._notes(item.currency, direction, lang),
            )

            if direction == "deposit":
                deposits.append(entry)
            else:
                withdrawals.append(entry)

        guidance = self._guidance(lang)

        return CashFlowView(
            year=dataset.year,
            deposits=deposits,
            withdrawals=withdrawals,
            guidance=guidance,
        )

    def _guidance(self, lang: str) -> list[str]:
        if lang == "en":
            return [
                "A deposit or withdrawal is not, by itself, a capital gain from selling shares.",
                "If the movement is in EUR and does not involve a new conversion, it is usually a simpler cash movement to justify.",
                "If the movement realizes cash outflows in foreign currency, there may be an additional FX tax effect.",
                "If you convert to EUR first and transfer later, the flow is usually clearer: sale, FX, withdrawal.",
            ]
        return [
            "Un ingreso o retiro no equivale por si mismo a una ganancia por venta de acciones.",
            "Si el movimiento es en EUR y no implica nueva conversion, suele ser un movimiento de caja mas simple de justificar.",
            "Si el movimiento materializa salida de efectivo en divisa extranjera, puede haber efecto fiscal adicional por diferencias de cambio.",
            "Cuando conviertes antes a EUR y luego transfieres, el flujo suele quedar mas claro: venta, FX, retirada.",
        ]

    def _fiscal_treatment(self, currency: str, direction: str, lang: str) -> str:
        if lang == "en":
            if direction == "deposit":
                return "Cash inflow movement; not a capital gain by itself."
            if currency == "EUR":
                return "Withdrawal in EUR: usually reflects already converted cash leaving the account."
            return "Withdrawal in foreign currency: review whether it realizes an extra FX difference."

        if direction == "deposit":
            return "Movimiento de entrada de caja; no es una ganancia patrimonial por si mismo."
        if currency == "EUR":
            return "Retiro en EUR: suele reflejar salida de caja ya convertida."
        return "Retiro en divisa: revisar si materializa diferencia de cambio adicional."

    def _notes(self, currency: str, direction: str, lang: str) -> list[str]:
        if lang == "en":
            if direction == "deposit":
                return [
                    "It is useful to link it to the later conversion if that cash is used to buy USD or assets.",
                ]
            if currency == "EUR":
                return [
                    "If the conversion to EUR already happened before the transfer, the withdrawal is usually easier to follow for tax purposes.",
                ]
            return [
                "If you kept foreign-currency cash after selling shares, this withdrawal may be part of the realized FX chain.",
            ]

        if direction == "deposit":
            return [
                "Conviene enlazarlo con la conversion posterior si ese efectivo se usa para comprar USD o activos.",
            ]
        if currency == "EUR":
            return [
                "Si la conversion a EUR ya ocurrio antes, el retiro suele ser mas limpio de seguir fiscalmente.",
            ]
        return [
            "Si mantuviste cash en divisa tras vender acciones, este retiro puede formar parte de la realizacion de FX.",
        ]
