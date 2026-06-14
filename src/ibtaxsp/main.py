from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ibtaxsp.models import WithdrawalSimulationRequest
from ibtaxsp.service import TaxService


ROOT = Path(__file__).resolve().parents[2]
service = TaxService(ROOT)

app = FastAPI(title="IBTaxSP API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/years")
def years() -> list[dict[str, str | int]]:
    return [item.model_dump() for item in service.list_available_years()]


@app.get("/api/overview")
def overview() -> dict:
    return service.get_overview().model_dump()


@app.get("/api/year/{year}")
def year_summary(year: int) -> dict:
    try:
        return service.get_year_summary(year).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/dataset")
def year_dataset(year: int) -> dict:
    try:
        return service.get_year_dataset(year).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/fifo")
def year_fifo(year: int) -> dict:
    try:
        return service.get_fifo_year_result(year).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/tax-summary")
def year_tax_summary(year: int, lang: str = "es") -> dict:
    try:
        return service.get_annual_tax_summary(year, lang).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/renta-view")
def year_renta_view(year: int, lang: str = "es") -> dict:
    try:
        return service.get_renta_view(year, lang).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/renta-guidance")
def year_renta_guidance(year: int, lang: str = "es") -> dict:
    try:
        return service.get_renta_guidance(year, lang).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/hacienda-view")
def year_hacienda_view(year: int, lang: str = "es") -> dict:
    try:
        return service.get_hacienda_view(year, lang).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.get("/api/year/{year}/cash-flow")
def year_cash_flow(year: int, lang: str = "es") -> dict:
    try:
        return service.get_cash_flow_view(year, lang).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {year} not found") from exc


@app.post("/api/simulate/withdrawal")
def simulate_withdrawal(request: WithdrawalSimulationRequest) -> dict:
    try:
        return service.simulate_withdrawal(request).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Year {request.year} not found") from exc
