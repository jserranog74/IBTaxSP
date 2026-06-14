from __future__ import annotations

from ibtaxsp.models import (
    AnnualTaxSummary,
    HaciendaChecklistItem,
    HaciendaEntry,
    HaciendaView,
)
from ibtaxsp.services.i18n import normalize_lang


class HaciendaViewBuilder:
    def build(self, summary: AnnualTaxSummary, lang: str = "es") -> HaciendaView:
        lang = normalize_lang(lang)
        if lang == "en":
            return self._build_en(summary)
        return self._build_es(summary)

    def _build_es(self, summary: AnnualTaxSummary) -> HaciendaView:
        entries = [
            HaciendaEntry(
                section="Base del ahorro",
                concept="Ganancias y perdidas patrimoniales por transmision de acciones/valores",
                amount_eur=summary.stock_gains.amount_eur,
                source="Calculo FIFO anual en EUR",
                notes=[
                    "Usar el informe FIFO como soporte justificativo.",
                    "No incluye eventos marcados como no soportados.",
                ],
            ),
            HaciendaEntry(
                section="Base del ahorro",
                concept="Ganancias y perdidas por divisa realizada",
                amount_eur=summary.fx_gains.amount_eur,
                source="FX transactions realizadas del ejercicio",
                notes=[
                    "Es independiente de la ganancia o perdida de las ventas de valores.",
                ],
            ),
            HaciendaEntry(
                section="Base del ahorro",
                concept="Dividendos integros",
                amount_eur=summary.dividends.amount_eur,
                source="Cash transactions tipo Dividends",
                notes=[
                    "Conviene cotejarlo con el detalle por dividendo y por fecha.",
                ],
            ),
            HaciendaEntry(
                section="Deducciones",
                concept="Retencion extranjera sobre dividendos para revisar doble imposicion internacional",
                amount_eur=summary.dividend_withholding.amount_eur,
                source="Cash transactions tipo Withholding Tax vinculadas a dividendos",
                notes=[
                    "La deduccion aplicable puede ser menor por los limites legales.",
                ],
            ),
            HaciendaEntry(
                section="Base del ahorro",
                concept="Intereses cobrados",
                amount_eur=summary.interest_received.amount_eur,
                source="Cash transactions tipo Broker Interest Received",
                notes=[
                    "Revisar junto con retenciones e intereses pagados si procede.",
                ],
            ),
        ]

        checklist = [
            HaciendaChecklistItem(
                label="Ganancias por ventas",
                status="ok",
                detail="Hay cifra anual y soporte FIFO lote a lote.",
            ),
            HaciendaChecklistItem(
                label="Dividendos y retenciones",
                status="ok",
                detail="Hay detalle por simbolo, fecha e importe bruto/retencion.",
            ),
            HaciendaChecklistItem(
                label="Divisa realizada",
                status="ok",
                detail="Hay total anual separado del bloque de valores.",
            ),
            HaciendaChecklistItem(
                label="Eventos no soportados",
                status="review" if summary.unsupported_fifo_events else "ok",
                detail=(
                    f"Hay {len(summary.unsupported_fifo_events)} eventos a revisar antes de presentar."
                    if summary.unsupported_fifo_events
                    else "No hay incidencias tecnicas abiertas."
                ),
            ),
        ]

        warnings = [
            "Los importes de esta vista son una ayuda operativa; la presentacion final debe revisar incidencias y limites fiscales.",
        ]
        if summary.unsupported_fifo_events:
            warnings.append(
                "No presentes la declaracion sin revisar las operaciones no soportadas que aparecen en la seccion de alertas."
            )

        return HaciendaView(
            year=summary.year,
            entries=entries,
            checklist=checklist,
            warnings=warnings,
        )

    def _build_en(self, summary: AnnualTaxSummary) -> HaciendaView:
        entries = [
            HaciendaEntry(
                section="Savings tax base",
                concept="Capital gains and losses from stock or securities disposals",
                amount_eur=summary.stock_gains.amount_eur,
                source="Annual FIFO calculation in EUR",
                notes=[
                    "Use the FIFO report as supporting evidence.",
                    "Unsupported events are excluded.",
                ],
            ),
            HaciendaEntry(
                section="Savings tax base",
                concept="Realized foreign exchange gains and losses",
                amount_eur=summary.fx_gains.amount_eur,
                source="Realized FX transactions for the year",
                notes=[
                    "This is independent from gains or losses on securities sales.",
                ],
            ),
            HaciendaEntry(
                section="Savings tax base",
                concept="Gross dividends",
                amount_eur=summary.dividends.amount_eur,
                source="Cash transactions of type Dividends",
                notes=[
                    "Cross-check against dividend-by-dividend detail and dates.",
                ],
            ),
            HaciendaEntry(
                section="Deductions",
                concept="Foreign withholding on dividends to review international double taxation",
                amount_eur=summary.dividend_withholding.amount_eur,
                source="Cash transactions of type Withholding Tax linked to dividends",
                notes=[
                    "The deductible amount may be lower because of legal limits.",
                ],
            ),
            HaciendaEntry(
                section="Savings tax base",
                concept="Interest received",
                amount_eur=summary.interest_received.amount_eur,
                source="Cash transactions of type Broker Interest Received",
                notes=[
                    "Review together with withholdings and paid interest if applicable.",
                ],
            ),
        ]

        checklist = [
            HaciendaChecklistItem(
                label="Security sale gains",
                status="ok",
                detail="Annual figure and lot-by-lot FIFO support are available.",
            ),
            HaciendaChecklistItem(
                label="Dividends and withholdings",
                status="ok",
                detail="Detail exists by symbol, date, and gross/withholding amount.",
            ),
            HaciendaChecklistItem(
                label="Realized FX",
                status="ok",
                detail="Annual total is separated from the securities block.",
            ),
            HaciendaChecklistItem(
                label="Unsupported events",
                status="review" if summary.unsupported_fifo_events else "ok",
                detail=(
                    f"There are {len(summary.unsupported_fifo_events)} events to review before filing."
                    if summary.unsupported_fifo_events
                    else "No open technical issues were detected."
                ),
            ),
        ]

        warnings = [
            "Amounts in this view are operational guidance; the final filing should still review tax limits and open issues.",
        ]
        if summary.unsupported_fifo_events:
            warnings.append(
                "Do not file before reviewing the unsupported operations shown in the alerts section."
            )

        return HaciendaView(
            year=summary.year,
            entries=entries,
            checklist=checklist,
            warnings=warnings,
        )
