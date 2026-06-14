from __future__ import annotations

from ibtaxsp.models import WithdrawalSimulationRequest, WithdrawalSimulationResult, YearDataset
from ibtaxsp.services.annual_tax import _RateBook
from ibtaxsp.services.i18n import normalize_lang


class SimulationService:
    def simulate_withdrawal(
        self,
        request: WithdrawalSimulationRequest,
        dataset: YearDataset,
        annual_fx_gain_eur: float,
    ) -> WithdrawalSimulationResult:
        lang = normalize_lang(request.lang)
        rate_book = _RateBook.from_datasets([dataset])
        ending_cash = self._extract_ending_cash(dataset)
        available_amount = ending_cash.get(request.currency, 0.0)
        feasible = request.amount <= available_amount + 1e-12
        estimated_cash_movement_eur = rate_book.convert_to_eur(
            request.amount,
            request.currency,
            dataset.year_end_positions[0].report_date if dataset.year_end_positions else f"{request.year}1231",
        )

        notes = self._notes_intro(lang)

        estimated_fx_component_eur = 0.0
        if request.currency != "EUR":
            estimated_fx_component_eur = annual_fx_gain_eur
            notes.append(self._note_foreign_currency(lang))
        else:
            notes.append(self._note_eur_withdrawal(lang))

        if not feasible:
            notes.append(self._note_not_feasible(lang))

        return WithdrawalSimulationResult(
            year=request.year,
            requested_amount=request.amount,
            currency=request.currency,
            available_amount=available_amount,
            feasible=feasible,
            estimated_fx_component_eur=estimated_fx_component_eur,
            estimated_cash_movement_eur=estimated_cash_movement_eur,
            notes=notes,
        )

    def _extract_ending_cash(self, dataset: YearDataset) -> dict[str, float]:
        result: dict[str, float] = {}
        for position in dataset.year_end_positions:
            if position.kind != "fx_lot":
                continue
            result[position.symbol_or_currency] = result.get(position.symbol_or_currency, 0.0) + position.quantity
        return result

    def _notes_intro(self, lang: str) -> list[str]:
        if lang == "en":
            return [
                "This simulation does not modify the real history or create persistent movements.",
                "The withdrawal itself does not re-tax a stock sale that was already realized.",
            ]
        return [
            "Esta simulacion no modifica el historico real ni genera movimientos persistentes.",
            "El retiro por si solo no vuelve a tributar la venta de acciones ya realizada.",
        ]

    def _note_foreign_currency(self, lang: str) -> str:
        if lang == "en":
            return "If you withdraw in foreign currency, there may be an FX tax component in addition to the cash movement itself."
        return "Si retiras en divisa extranjera, puede haber componente fiscal de FX ademas del simple movimiento de caja."

    def _note_eur_withdrawal(self, lang: str) -> str:
        if lang == "en":
            return "If you convert to EUR first and then withdraw, the flow is usually easier to follow."
        return "Si ya conviertes antes a EUR y luego retiras, el flujo suele ser mas facil de seguir."

    def _note_not_feasible(self, lang: str) -> str:
        if lang == "en":
            return "The requested amount exceeds the detected year-end balance in that currency."
        return "El importe solicitado supera el saldo de cierre detectado en esa divisa."
