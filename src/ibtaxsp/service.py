from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ibtaxsp.models import (
    AvailableYear,
    AnnualTaxSummary,
    CashFlowView,
    FifoYearResult,
    HaciendaView,
    OverviewResponse,
    RentaGuidance,
    RentaView,
    WithdrawalSimulationRequest,
    WithdrawalSimulationResult,
    YearDataset,
    YearSummary,
)
from ibtaxsp.services.hacienda_view import HaciendaViewBuilder
from ibtaxsp.services.annual_tax import AnnualTaxCalculator
from ibtaxsp.services.cash_flow_view import CashFlowViewBuilder
from ibtaxsp.services.simulation import SimulationService
from ibtaxsp.repository import TaxDataRepository
from ibtaxsp.services.fifo_engine import FifoEngine
from ibtaxsp.services.flex_parser import FlexYearParser
from ibtaxsp.services.renta_guidance import RentaGuidanceBuilder
from ibtaxsp.services.renta_view import RentaViewBuilder


class TaxService:
    def __init__(self, root: Path) -> None:
        self.repository = TaxDataRepository(root)
        self.parser = FlexYearParser()
        self.fifo_engine = FifoEngine()
        self.annual_tax_calculator = AnnualTaxCalculator()
        self.cash_flow_view_builder = CashFlowViewBuilder()
        self.hacienda_view_builder = HaciendaViewBuilder()
        self.renta_guidance_builder = RentaGuidanceBuilder()
        self.renta_view_builder = RentaViewBuilder()
        self.simulation_service = SimulationService()

    def list_available_years(self) -> list[AvailableYear]:
        return [
            AvailableYear(year=item.year, xml_path=str(item.xml_path))
            for item in self.repository.list_year_files()
        ]

    @lru_cache(maxsize=16)
    def get_year_summary(self, year: int) -> YearSummary:
        year_file = self.repository.get_year_file(year)
        if year_file is None:
            raise KeyError(year)
        return self.parser.parse_year_summary(year, year_file.xml_path)

    @lru_cache(maxsize=8)
    def get_year_dataset(self, year: int) -> YearDataset:
        year_file = self.repository.get_year_file(year)
        if year_file is None:
            raise KeyError(year)
        return self.parser.parse_year_dataset(year, year_file.xml_path)

    def get_overview(self) -> OverviewResponse:
        years = [self.get_year_summary(item.year) for item in self.repository.list_year_files()]
        return OverviewResponse(years=years)

    @lru_cache(maxsize=8)
    def get_fifo_year_result(self, year: int) -> FifoYearResult:
        available_years = [item.year for item in self.repository.list_year_files()]
        if year not in available_years:
            raise KeyError(year)
        datasets = [self.get_year_dataset(item_year) for item_year in available_years if item_year <= year]
        return self.fifo_engine.compute(datasets, year)

    @lru_cache(maxsize=8)
    def get_annual_tax_summary(self, year: int, lang: str = "es") -> AnnualTaxSummary:
        available_years = [item.year for item in self.repository.list_year_files()]
        if year not in available_years:
            raise KeyError(year)

        datasets = [self.get_year_dataset(item_year) for item_year in available_years if item_year <= year]
        fifo_result = self.fifo_engine.compute(datasets, year)

        year_dataset = next(item for item in datasets if item.year == year)
        fx_gain_usd = sum(item.realized_pl for item in year_dataset.fx_transactions)
        fx_gain_eur = sum(
            self._usd_to_eur(item.realized_pl, item.report_date, datasets) for item in year_dataset.fx_transactions
        )

        return self.annual_tax_calculator.build_summary(
            year=year,
            datasets=datasets,
            stock_gain_eur=fifo_result.total_gain_eur,
            stock_gain_usd=fifo_result.total_gain_usd,
            fx_gain_eur=fx_gain_eur,
            fx_gain_usd=fx_gain_usd,
            unsupported_fifo_events=fifo_result.unsupported_events,
            lang=lang,
        )

    def _usd_to_eur(self, amount_usd: float, report_date: str, datasets: list[YearDataset]) -> float:
        rates = {}
        for dataset in datasets:
            for rate in dataset.conversion_rates:
                if rate.report_date == report_date:
                    rates[(rate.from_currency, rate.to_currency)] = rate.rate
        eur_usd = rates.get(("EUR", "USD"))
        if not eur_usd:
            raise KeyError(f"Missing EUR/USD rate for {report_date}")
        return amount_usd / eur_usd

    @lru_cache(maxsize=8)
    def get_renta_view(self, year: int, lang: str = "es") -> RentaView:
        available_years = [item.year for item in self.repository.list_year_files()]
        if year not in available_years:
            raise KeyError(year)

        datasets = [self.get_year_dataset(item_year) for item_year in available_years if item_year <= year]
        tax_summary = self.get_annual_tax_summary(year, lang)
        fifo_result = self.get_fifo_year_result(year)
        return self.renta_view_builder.build(year, datasets, tax_summary, fifo_result)

    @lru_cache(maxsize=8)
    def get_renta_guidance(self, year: int, lang: str = "es") -> RentaGuidance:
        if year not in [item.year for item in self.repository.list_year_files()]:
            raise KeyError(year)
        summary = self.get_annual_tax_summary(year, lang)
        renta_view = self.get_renta_view(year, lang)
        return self.renta_guidance_builder.build(summary, renta_view, lang)

    @lru_cache(maxsize=8)
    def get_hacienda_view(self, year: int, lang: str = "es") -> HaciendaView:
        if year not in [item.year for item in self.repository.list_year_files()]:
            raise KeyError(year)
        summary = self.get_annual_tax_summary(year, lang)
        return self.hacienda_view_builder.build(summary, lang)

    @lru_cache(maxsize=8)
    def get_cash_flow_view(self, year: int, lang: str = "es") -> CashFlowView:
        if year not in [item.year for item in self.repository.list_year_files()]:
            raise KeyError(year)
        dataset = self.get_year_dataset(year)
        return self.cash_flow_view_builder.build(dataset, lang)

    def simulate_withdrawal(self, request: WithdrawalSimulationRequest) -> WithdrawalSimulationResult:
        if request.year not in [item.year for item in self.repository.list_year_files()]:
            raise KeyError(request.year)
        dataset = self.get_year_dataset(request.year)
        annual_summary = self.get_annual_tax_summary(request.year, request.lang)
        return self.simulation_service.simulate_withdrawal(
            request=request,
            dataset=dataset,
            annual_fx_gain_eur=annual_summary.fx_gains.amount_eur,
        )
