from __future__ import annotations

from ibtaxsp.models import AnnualTaxSummary, RentaGuidance, RentaInputBlock
from ibtaxsp.services.i18n import normalize_lang


class RentaGuidanceBuilder:
    def build(self, summary: AnnualTaxSummary, lang: str = "es") -> RentaGuidance:
        lang = normalize_lang(lang)
        if lang == "en":
            return self._build_en(summary)
        return self._build_es(summary)

    def _build_es(self, summary: AnnualTaxSummary) -> RentaGuidance:
        blocks = [
            RentaInputBlock(
                title="Ganancias y perdidas patrimoniales por ventas de valores",
                description="Resultado anual de transmisiones de acciones y otros valores homogeneos calculado con FIFO en EUR.",
                amount_eur=summary.stock_gains.amount_eur,
                review_notes=[
                    "Conviene revisar operaciones marcadas como no soportadas antes de dar esta cifra por cerrada.",
                    "El detalle justificativo debe salir del informe FIFO por venta y por lote consumido.",
                ],
            ),
            RentaInputBlock(
                title="Ganancias y perdidas por divisa realizada",
                description="Resultado por realizacion de moneda extranjera distinto del de las ventas de valores.",
                amount_eur=summary.fx_gains.amount_eur,
                review_notes=[
                    "No duplica la ganancia de la venta de acciones; refleja solo el efecto adicional del cash en divisa.",
                    "Debe revisarse junto con conversiones y pagos/cobros en moneda extranjera.",
                ],
            ),
            RentaInputBlock(
                title="Dividendos integros",
                description="Importe bruto de dividendos cobrado en el ejercicio, convertido a EUR.",
                amount_eur=summary.dividends.amount_eur,
                review_notes=[
                    "Se complementa con la retencion extranjera soportada para la posible deduccion por doble imposicion.",
                ],
            ),
            RentaInputBlock(
                title="Retencion extranjera sobre dividendos",
                description="Retencion soportada en origen sobre dividendos extranjeros.",
                amount_eur=summary.dividend_withholding.amount_eur,
                review_notes=[
                    "La deduccion por doble imposicion internacional no siempre coincide al 100 % con esta cifra; hay que aplicar el limite fiscal correspondiente.",
                ],
            ),
            RentaInputBlock(
                title="Intereses cobrados",
                description="Rendimientos positivos del efectivo del broker convertidos a EUR.",
                amount_eur=summary.interest_received.amount_eur,
                review_notes=[
                    "Puede coexistir con retenciones asociadas a intereses en algunas divisas o productos.",
                ],
            ),
            RentaInputBlock(
                title="Intereses y costes financieros pagados",
                description="Cargos por intereses o costes similares informados por IB en el ejercicio.",
                amount_eur=summary.interest_paid.amount_eur,
                review_notes=[
                    "Conviene revisar su tratamiento concreto en funcion del tipo de operacion y de como decidas declarar el resto del ejercicio.",
                ],
            ),
        ]

        action_items = [
            "Revisar que no queden eventos no soportados antes de trasladar importes a la declaracion.",
            "Usar el informe FIFO anual como soporte de las ventas declaradas.",
            "Usar el detalle de dividendos y retenciones para comprobar la doble imposicion internacional.",
            "Conservar los extractos Flex Query y este resumen por si Hacienda pide justificacion.",
        ]

        caveats = [
            "Esta ayuda organiza importes para la declaracion, pero no sustituye una validacion fiscal final si tienes casos especiales.",
            "Las ventas en corto, transferencias complejas o historicos incompletos deben revisarse antes de presentar.",
        ]

        return RentaGuidance(
            year=summary.year,
            blocks=blocks,
            action_items=action_items,
            caveats=caveats,
        )

    def _build_en(self, summary: AnnualTaxSummary) -> RentaGuidance:
        blocks = [
            RentaInputBlock(
                title="Capital gains and losses from securities sales",
                description="Annual result from stock and similar securities disposals calculated with FIFO in EUR.",
                amount_eur=summary.stock_gains.amount_eur,
                review_notes=[
                    "Review unsupported operations before treating this amount as final.",
                    "Supporting detail should come from the FIFO report by sale and by consumed lot.",
                ],
            ),
            RentaInputBlock(
                title="Realized foreign exchange gains and losses",
                description="Result from realized foreign currency movements separate from stock sales.",
                amount_eur=summary.fx_gains.amount_eur,
                review_notes=[
                    "This does not duplicate stock sale gains; it only reflects the extra cash FX effect.",
                    "Review it together with conversions and foreign-currency receipts or payments.",
                ],
            ),
            RentaInputBlock(
                title="Gross dividends",
                description="Gross dividend income received during the year, converted to EUR.",
                amount_eur=summary.dividends.amount_eur,
                review_notes=[
                    "Use it together with foreign withholding to assess international double-tax relief.",
                ],
            ),
            RentaInputBlock(
                title="Foreign withholding on dividends",
                description="Withholding tax paid at source on foreign dividends.",
                amount_eur=summary.dividend_withholding.amount_eur,
                review_notes=[
                    "International double-tax relief may be lower than this amount because of legal limits.",
                ],
            ),
            RentaInputBlock(
                title="Interest received",
                description="Positive cash yield from the broker converted to EUR.",
                amount_eur=summary.interest_received.amount_eur,
                review_notes=[
                    "It may coexist with interest-related withholding in some currencies or products.",
                ],
            ),
            RentaInputBlock(
                title="Interest and financing costs paid",
                description="Interest charges or similar costs reported by IB during the year.",
                amount_eur=summary.interest_paid.amount_eur,
                review_notes=[
                    "Review its exact tax treatment depending on the operation type and how you file the rest of the year.",
                ],
            ),
        ]

        action_items = [
            "Confirm there are no unsupported events before moving figures into the tax return.",
            "Use the annual FIFO report as support for declared securities sales.",
            "Use dividend and withholding detail to review international double taxation.",
            "Keep the Flex Query statements and this summary in case the tax agency requests support.",
        ]

        caveats = [
            "This view organizes figures for filing, but it does not replace a final tax review for special cases.",
            "Short sales, complex transfers, or incomplete history should be checked before filing.",
        ]

        return RentaGuidance(
            year=summary.year,
            blocks=blocks,
            action_items=action_items,
            caveats=caveats,
        )
