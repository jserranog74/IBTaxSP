from __future__ import annotations

from ibtaxsp.models import (
    AnnualTaxSummary,
    RentaFilingLine,
    RentaGuidance,
    RentaInputBlock,
    RentaView,
)
from ibtaxsp.services.i18n import normalize_lang


class RentaGuidanceBuilder:
    def build(self, summary: AnnualTaxSummary, renta_view: RentaView, lang: str = "es") -> RentaGuidance:
        lang = normalize_lang(lang)
        if lang == "en":
            return self._build_en(summary, renta_view)
        return self._build_es(summary, renta_view)

    def _build_es(self, summary: AnnualTaxSummary, renta_view: RentaView) -> RentaGuidance:
        blocks = [
            RentaInputBlock(
                title="Ganancias y perdidas patrimoniales por ventas de valores",
                description="Resultado anual de transmisiones de acciones y otros valores homogeneos calculado con FIFO en EUR.",
                amount_eur=summary.stock_gains.amount_eur,
                review_notes=[
                    "Conviene revisar operaciones marcadas como no soportadas antes de dar esta cifra por cerrada.",
                    "El detalle justificativo debe salir del informe FIFO por venta y por lote consumido.",
                ],
                filing_reference_title=self._reference_title_es(summary.year),
                filing_references=self._stock_references_es(summary.year),
            ),
            RentaInputBlock(
                title="Ganancias y perdidas por divisa realizada",
                description="Resultado por realizacion de moneda extranjera distinto del de las ventas de valores.",
                amount_eur=summary.fx_gains.amount_eur,
                review_notes=[
                    "No duplica la ganancia de la venta de acciones; refleja solo el efecto adicional del cash en divisa.",
                    "Debe revisarse junto con conversiones y pagos/cobros en moneda extranjera.",
                ],
                filing_reference_title=self._reference_title_es(summary.year),
                filing_references=self._fx_references_es(summary.year),
            ),
            RentaInputBlock(
                title="Dividendos integros",
                description="Importe bruto de dividendos cobrado en el ejercicio, convertido a EUR.",
                amount_eur=summary.dividends.amount_eur,
                review_notes=[
                    "Se complementa con la retencion extranjera soportada para la posible deduccion por doble imposicion.",
                ],
                filing_reference_title=self._reference_title_es(summary.year),
                filing_references=self._dividend_references_es(summary.year),
            ),
            RentaInputBlock(
                title="Retencion extranjera sobre dividendos",
                description="Retencion soportada en origen sobre dividendos extranjeros.",
                amount_eur=summary.dividend_withholding.amount_eur,
                review_notes=[
                    "La deduccion por doble imposicion internacional no siempre coincide al 100 % con esta cifra; hay que aplicar el limite fiscal correspondiente.",
                ],
                filing_reference_title=self._reference_title_es(summary.year),
                filing_references=self._withholding_references_es(summary.year),
            ),
            RentaInputBlock(
                title="Intereses cobrados",
                description="Rendimientos positivos del efectivo del broker convertidos a EUR.",
                amount_eur=summary.interest_received.amount_eur,
                review_notes=[
                    "Puede coexistir con retenciones asociadas a intereses en algunas divisas o productos.",
                ],
                filing_reference_title=self._reference_title_es(summary.year),
                filing_references=self._interest_references_es(summary.year),
            ),
            RentaInputBlock(
                title="Intereses y costes financieros pagados",
                description="Cargos por intereses o costes similares informados por IB en el ejercicio.",
                amount_eur=summary.interest_paid.amount_eur,
                review_notes=[
                    "Conviene revisar su tratamiento concreto en funcion del tipo de operacion y de como decidas declarar el resto del ejercicio.",
                ],
                filing_reference_title=self._reference_title_es(summary.year),
                filing_references=self._interest_paid_references_es(summary.year),
            ),
        ]

        filing_lines = self._filing_lines_es(summary, renta_view)

        action_items = [
            "Revisar que no queden eventos no soportados antes de trasladar importes a la declaracion.",
            "Usar el informe FIFO anual como soporte de las ventas declaradas.",
            "Usar el detalle de dividendos y retenciones para comprobar la doble imposicion internacional.",
            "Conservar los extractos Flex Query y este resumen por si Hacienda pide justificacion.",
        ]

        caveats = [
            "Estas referencias de casillas son orientativas y deben revisarse en Renta Web del ejercicio correspondiente.",
            "Las ventas en corto complejas, transferencias especiales o historicos incompletos deben revisarse antes de presentar.",
        ]

        return RentaGuidance(
            year=summary.year,
            blocks=blocks,
            filing_lines=filing_lines,
            fx_filing_entries=renta_view.fx_filing_entries,
            action_items=action_items,
            caveats=caveats,
        )

    def _build_en(self, summary: AnnualTaxSummary, renta_view: RentaView) -> RentaGuidance:
        blocks = [
            RentaInputBlock(
                title="Capital gains and losses from securities sales",
                description="Annual result from stock and similar securities disposals calculated with FIFO in EUR.",
                amount_eur=summary.stock_gains.amount_eur,
                review_notes=[
                    "Review unsupported operations before treating this amount as final.",
                    "Supporting detail should come from the FIFO report by sale and by consumed lot.",
                ],
                filing_reference_title=self._reference_title_en(summary.year),
                filing_references=self._stock_references_en(summary.year),
            ),
            RentaInputBlock(
                title="Realized foreign exchange gains and losses",
                description="Result from realized foreign currency movements separate from stock sales.",
                amount_eur=summary.fx_gains.amount_eur,
                review_notes=[
                    "This does not duplicate stock sale gains; it only reflects the extra cash FX effect.",
                    "Review it together with conversions and foreign-currency receipts or payments.",
                ],
                filing_reference_title=self._reference_title_en(summary.year),
                filing_references=self._fx_references_en(summary.year),
            ),
            RentaInputBlock(
                title="Gross dividends",
                description="Gross dividend income received during the year, converted to EUR.",
                amount_eur=summary.dividends.amount_eur,
                review_notes=[
                    "Use it together with foreign withholding to assess international double-tax relief.",
                ],
                filing_reference_title=self._reference_title_en(summary.year),
                filing_references=self._dividend_references_en(summary.year),
            ),
            RentaInputBlock(
                title="Foreign withholding on dividends",
                description="Withholding tax paid at source on foreign dividends.",
                amount_eur=summary.dividend_withholding.amount_eur,
                review_notes=[
                    "International double-tax relief may be lower than this amount because of legal limits.",
                ],
                filing_reference_title=self._reference_title_en(summary.year),
                filing_references=self._withholding_references_en(summary.year),
            ),
            RentaInputBlock(
                title="Interest received",
                description="Positive cash yield from the broker converted to EUR.",
                amount_eur=summary.interest_received.amount_eur,
                review_notes=[
                    "It may coexist with interest-related withholding in some currencies or products.",
                ],
                filing_reference_title=self._reference_title_en(summary.year),
                filing_references=self._interest_references_en(summary.year),
            ),
            RentaInputBlock(
                title="Interest and financing costs paid",
                description="Interest charges or similar costs reported by IB during the year.",
                amount_eur=summary.interest_paid.amount_eur,
                review_notes=[
                    "Review its exact tax treatment depending on the operation type and how you file the rest of the year.",
                ],
                filing_reference_title=self._reference_title_en(summary.year),
                filing_references=self._interest_paid_references_en(summary.year),
            ),
        ]

        filing_lines = self._filing_lines_en(summary, renta_view)

        action_items = [
            "Confirm there are no unsupported events before moving figures into the tax return.",
            "Use the annual FIFO report as support for declared securities sales.",
            "Use dividend and withholding detail to review international double taxation.",
            "Keep the Flex Query statements and this summary in case the tax agency requests support.",
        ]

        caveats = [
            "These box references are indicative and should still be checked against the corresponding tax-year version of Renta Web.",
            "Complex short sales, special transfers, or incomplete history should be checked before filing.",
        ]

        return RentaGuidance(
            year=summary.year,
            blocks=blocks,
            filing_lines=filing_lines,
            fx_filing_entries=renta_view.fx_filing_entries,
            action_items=action_items,
            caveats=caveats,
        )

    def _filing_lines_es(self, summary: AnnualTaxSummary, renta_view: RentaView) -> list[RentaFilingLine]:
        lines = [
            RentaFilingLine(
                section="Acciones cotizadas",
                concept=f"{item.symbol} - ganancia patrimonial",
                amount_eur=item.gain_eur,
                destination="F2 - Acciones admitidas a negociacion",
                box_reference=None,
                entry_method="Alta manual por emisora o uso de Cartera de Valores.",
                issuer_name=item.issuer_name,
                transmission_value_eur=item.proceeds_eur,
                acquisition_value_eur=item.basis_eur,
                mark_reinvestment_check=False,
                mark_repurchase_loss_check=False,
                mark_dt9_check=False,
                notes=[
                    f"{item.disposition_count} ventas agregadas en el ejercicio.",
                    f"Emisora: {item.issuer_name}." if item.issuer_name else "En Renta Web suele importar la sociedad emisora, no el broker.",
                ],
            )
            for item in renta_view.gains_by_symbol
        ]
        lines.extend(
            [
                RentaFilingLine(
                    section="Ganancias patrimoniales",
                    concept="Divisa realizada",
                    amount_eur=summary.fx_gains.amount_eur,
                    destination="F2 - Otros elementos patrimoniales",
                    box_reference=None,
                    entry_method="Alta manual en F2 como otros elementos patrimoniales; mejor una linea agregada anual si no vas evento a evento.",
                    suggested_description="Divisa USD - Interactive Brokers",
                    notes=[
                        "Pantalla AEAT habitual: titularidad del contribuyente, casilla 1625 sin marcar, clave 4 y operacion onerosa 1612 marcada; no marcar 1613.",
                        "Tipo de elemento patrimonial: Clave 4 - Otros elementos patrimoniales no afectos a actividades economicas.",
                        "Si cargas una sola linea anual, usa como valor de adquisicion el coste total EUR de la divisa realizada y como valor de transmision su contravalor total EUR al realizarla.",
                        "Las casillas 1634, 1636, 1642 y 1644 normalmente se dejan vacias si no aplica ninguna exencion o reduccion especial.",
                        "La casilla 1640 la calcula Renta Web automaticamente como diferencia positiva entre transmision y adquisicion.",
                        "Si Renta Web te exige una fecha unica de adquisicion y otra de transmision, es preferible desglosar por eventos en lugar de inventar fechas para una linea anual agregada.",
                        "Si prefieres mas soporte documental, puedes desglosarla por eventos en vez de meterla agregada.",
                    ],
                ),
                RentaFilingLine(
                    section="Capital mobiliario",
                    concept="Dividendos integros",
                    amount_eur=summary.dividends.amount_eur,
                    destination="Capital mobiliario - Dividendos y otros rendimientos por participacion en fondos propios",
                    box_reference=None,
                    entry_method="Introducir el importe bruto; las retenciones se trasladan por el programa.",
                    notes=["Base del ahorro, dividendos y participacion en fondos propios."],
                ),
                RentaFilingLine(
                    section="Deducciones",
                    concept="Doble imposicion internacional por dividendos",
                    amount_eur=summary.dividend_withholding.amount_eur,
                    destination="Deducciones",
                    box_reference="0588",
                    entry_method="Introducir el impuesto soportado deducible con el limite legal aplicable.",
                    notes=[
                        "Referencia habitual: casilla 0588, con limite legal aplicable.",
                        (
                            "Ventana habitual de captura: trabajo extranjero 0,00; otros rendimientos netos "
                            f"{summary.dividends.amount_eur:.2f}".replace(".", ",")
                            + "; ganancias patrimoniales 0,00; impuesto satisfecho en el extranjero "
                            + f"{summary.dividend_withholding.amount_eur:.2f}".replace(".", ",")
                            + "."
                        ),
                    ],
                ),
                RentaFilingLine(
                    section="Capital mobiliario",
                    concept="Intereses cobrados",
                    amount_eur=summary.interest_received.amount_eur,
                    destination="Capital mobiliario - Intereses de cuentas, depositos y activos financieros",
                    box_reference=None,
                    entry_method="Introducir el importe integro; las retenciones se trasladan por Renta Web.",
                    notes=["Base del ahorro, intereses de cuentas, depositos y activos financieros."],
                ),
            ]
        )
        if summary.interest_paid.amount_eur > 0:
            lines.append(
                RentaFilingLine(
                    section="Revision manual",
                    concept="Intereses y costes financieros pagados",
                    amount_eur=summary.interest_paid.amount_eur,
                    destination="Revisar antes de trasladar",
                    box_reference=None,
                    entry_method="No mover automaticamente sin validar el tratamiento exacto.",
                    notes=["No trasladar automaticamente sin revisar el tratamiento exacto en Renta Web."],
                )
            )
        return lines

    def _filing_lines_en(self, summary: AnnualTaxSummary, renta_view: RentaView) -> list[RentaFilingLine]:
        lines = [
            RentaFilingLine(
                section="Listed shares",
                concept=f"{item.symbol} - capital gain",
                amount_eur=item.gain_eur,
                destination="F2 - Listed shares",
                box_reference=None,
                entry_method="Manual line by issuer or use of the Securities Portfolio tool.",
                issuer_name=item.issuer_name,
                transmission_value_eur=item.proceeds_eur,
                acquisition_value_eur=item.basis_eur,
                mark_reinvestment_check=False,
                mark_repurchase_loss_check=False,
                mark_dt9_check=False,
                notes=[
                    f"{item.disposition_count} aggregated sales in the year.",
                    f"Issuer: {item.issuer_name}." if item.issuer_name else "Renta Web usually cares about the issuer, not the broker.",
                ],
            )
            for item in renta_view.gains_by_symbol
        ]
        lines.extend(
            [
                RentaFilingLine(
                    section="Capital gains",
                    concept="Realized FX",
                    amount_eur=summary.fx_gains.amount_eur,
                    destination="F2 - Other capital assets",
                    box_reference=None,
                    entry_method="Manual F2 entry as other capital assets; usually one annual aggregated line if you are not reporting event by event.",
                    suggested_description="USD currency - Interactive Brokers",
                    notes=[
                        "Typical AEAT screen: taxpayer ownership, box 1625 unchecked, key 4 selected, onerous transfer 1612 checked, and 1613 unchecked.",
                        "Asset type: Key 4 - Other capital assets not related to economic activities.",
                        "If you enter a single annual line, use the total EUR cost of the realized currency as acquisition value and its total EUR proceeds as transmission value.",
                        "Boxes 1634, 1636, 1642, and 1644 are usually left blank unless a specific exemption or special reduction applies.",
                        "Box 1640 is normally computed by Renta Web as the positive difference between transfer and acquisition values.",
                        "If Renta Web forces you to provide a single acquisition date and a single transmission date, it is safer to split by events instead of inventing dates for one annual aggregated line.",
                        "If you want more audit detail, you can split it event by event instead of using one aggregated line.",
                    ],
                ),
                RentaFilingLine(
                    section="Investment income",
                    concept="Gross dividends",
                    amount_eur=summary.dividends.amount_eur,
                    destination="Investment income - Dividends and similar equity income",
                    box_reference=None,
                    entry_method="Enter the gross amount; withholding is moved by the program.",
                    notes=["Savings base, dividends and similar equity income."],
                ),
                RentaFilingLine(
                    section="Deductions",
                    concept="International double taxation on dividends",
                    amount_eur=summary.dividend_withholding.amount_eur,
                    destination="Deductions",
                    box_reference="0588",
                    entry_method="Enter the deductible foreign tax subject to the legal limit.",
                    notes=["Usual reference: box 0588, subject to the legal limit."],
                ),
                RentaFilingLine(
                    section="Investment income",
                    concept="Interest received",
                    amount_eur=summary.interest_received.amount_eur,
                    destination="Investment income - Interest from accounts, deposits, and financial assets",
                    box_reference=None,
                    entry_method="Enter the gross amount; withholding is moved by Renta Web.",
                    notes=["Savings base, interest from accounts, deposits, and financial assets."],
                ),
            ]
        )
        if summary.interest_paid.amount_eur > 0:
            lines.append(
                RentaFilingLine(
                    section="Manual review",
                    concept="Interest and financing costs paid",
                    amount_eur=summary.interest_paid.amount_eur,
                    destination="Review before filing",
                    box_reference=None,
                    entry_method="Do not move automatically until the exact treatment is confirmed.",
                    notes=["Do not move automatically without checking the exact treatment in Renta Web."],
                )
            )
        return lines

    def _reference_title_es(self, year: int) -> str:
        return f"Referencia orientativa AEAT para el ejercicio {year}"

    def _reference_title_en(self, year: int) -> str:
        return f"Indicative AEAT reference for tax year {year}"

    def _stock_references_es(self, year: int) -> list[str]:
        return [
            f"Ejercicio {year}: apartado F2 de ganancias y perdidas patrimoniales por transmision de acciones admitidas a negociacion.",
            "Si lo prefieres, Renta Web permite usar Cartera de Valores en vez de alta manual por operacion.",
        ]

    def _stock_references_en(self, year: int) -> list[str]:
        return [
            f"Tax year {year}: section F2 for capital gains and losses from listed share disposals.",
            "If preferred, Renta Web can use the Securities Portfolio tool instead of manual entries.",
        ]

    def _fx_references_es(self, year: int) -> list[str]:
        return [
            f"Ejercicio {year}: orientativamente en F2 como transmision de otros elementos patrimoniales.",
            "Conviene revisar en Renta Web si te resulta mas claro declararlo agregado o evento a evento.",
        ]

    def _fx_references_en(self, year: int) -> list[str]:
        return [
            f"Tax year {year}: indicative fit under F2 as disposals of other capital assets.",
            "Check in Renta Web whether it is clearer to report it aggregated or event by event.",
        ]

    def _dividend_references_es(self, year: int) -> list[str]:
        return [
            f"Ejercicio {year}: rendimientos del capital mobiliario a integrar en la base del ahorro, apartado de dividendos y otros rendimientos por participacion en fondos propios.",
            "Las retenciones practicadas sobre capital mobiliario se trasladan a la casilla 0597 por el propio programa.",
        ]

    def _dividend_references_en(self, year: int) -> list[str]:
        return [
            f"Tax year {year}: movable capital income in the savings base, dividends and similar income from equity participation.",
            "Withholding on movable capital income is moved by the program into box 0597.",
        ]

    def _withholding_references_es(self, year: int) -> list[str]:
        return [
            f"Ejercicio {year}: deduccion por doble imposicion internacional, habitualmente casilla 0588.",
            "La deduccion aplicable es el menor entre el impuesto satisfecho en el extranjero y el limite que corresponda en Espana.",
        ]

    def _withholding_references_en(self, year: int) -> list[str]:
        return [
            f"Tax year {year}: international double taxation relief, usually box 0588.",
            "The usable deduction is the lower of the foreign tax actually paid and the Spanish limit.",
        ]

    def _interest_references_es(self, year: int) -> list[str]:
        return [
            f"Ejercicio {year}: rendimientos del capital mobiliario a integrar en la base del ahorro, apartado de intereses de cuentas, depositos y activos financieros.",
            "Las retenciones de estos rendimientos tambien se trasladan a la casilla 0597 por Renta Web.",
        ]

    def _interest_references_en(self, year: int) -> list[str]:
        return [
            f"Tax year {year}: movable capital income in the savings base, interest from accounts, deposits, and financial assets.",
            "Withholding for these amounts is also moved by Renta Web into box 0597.",
        ]

    def _interest_paid_references_es(self, year: int) -> list[str]:
        return [
            f"Ejercicio {year}: no lo muevas automaticamente a una casilla sin revisar el origen exacto del cargo.",
            "Si procede de intereses del broker o costes financieros, conviene validarlo antes en Renta Web o con asesor fiscal.",
        ]

    def _interest_paid_references_en(self, year: int) -> list[str]:
        return [
            f"Tax year {year}: do not move this automatically into a box without checking the exact source of the charge.",
            "If it comes from broker interest or financing costs, validate the treatment first in Renta Web or with a tax advisor.",
        ]
