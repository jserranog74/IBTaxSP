# IBTaxSP

IBTaxSP is a local web tool to review Interactive Brokers yearly activity and prepare a traceable Spanish tax workflow around:

- stock sales under FIFO
  <img width="1435" height="1099" alt="image" src="https://github.com/user-attachments/assets/20866876-b84f-4920-bec1-869c1b76fbc9" />
- EUR/USD cash movements
- foreign exchange effects
- dividends and withholdings
- annual support views for filing
  <img width="1208" height="1229" alt="image" src="https://github.com/user-attachments/assets/ee6461dc-2fdc-4696-b89a-32dd58ec8a2d" />

The project is designed to help you understand and document the numbers behind your annual filing. It is not tax advice and does not replace a professional review.

## What It Does

- reads yearly `ibtax_full.xml` Flex Query exports from Interactive Brokers
- builds yearly summaries for cash, positions, trades, and FX
- calculates FIFO-based stock disposals
- separates stock gains from realized FX effects
- prepares practical views for filing and audit support
- includes a withdrawal simulation that does not modify real imported history
- supports Spanish and English in the web UI

## Private Data

Real Interactive Brokers exports should stay private.

This repository is configured so that these folders are ignored by Git:

- `IB/Tax`
- `IB/Reports`

Recommended yearly structure:

```text
IB/Tax/2023/ibtax_full.xml
IB/Tax/2024/ibtax_full.xml
IB/Tax/2025/ibtax_full.xml
```

## Interactive Brokers Export

The main source used by this project is an Activity Flex Query export that includes, at minimum:

- `Trades`
- `Cash Transactions`
- `Statement of Funds`
- `Transfers`
- `Open Positions`
- `Forex Balances`
- `Conversion Rates`

The project currently expects yearly files named `ibtax_full.xml`.

## How To Export From Interactive Brokers

Use an `Activity Flex Query` in Interactive Brokers.

Suggested setup:

- `Query name`: `ibtax_full`
- `Format`: `XML`
- `Date format`: `yyyyMMdd`
- `Time format`: `HHmmss`
- `Date/Time separator`: `;`
- `Include currency rates`: `Yes`
- `Include audit trail fields`: `Yes`
- `Include offsetting trade/cancel pairs`: `Yes`
- `Breakout by day`: `No`

Recommended period:

- export one file per fiscal year
- if IB allows it, use a custom annual period covering `01 January` to `31 December`
- if the annual export is not available in one shot, generate the broadest yearly XML you can and keep one final file per year

Sections to include:

- `Account Information`
- `Cash Report`
- `Cash Transactions`
- `Financial Instrument Information`
- `Forex Balances`
- `Open Positions`
- `Prior Period Positions`
- `Statement of Funds`
- `Trades`
- `Transfers`

Strongly recommended when available:

- `Realized and Unrealized Performance Summary in Base`
- `Change in Position Value Summary`
- `Transaction Fees`
- `Interest Accruals`
- `Interest Details (Tiers)`
- `Option Exercises, Assignments and Expirations`
- `Corporate Actions`

Current import convention in this project:

- save each year as `ibtax_full.xml`
- place it in `IB/Tax/<year>/`

Example:

```text
IB/Tax/2023/ibtax_full.xml
IB/Tax/2024/ibtax_full.xml
IB/Tax/2025/ibtax_full.xml
```

Notes:

- `XML` is the primary supported source right now
- this project is built around yearly files, not monthly fragments
- if you have older positions before your first imported year, import as much history as IB lets you export
- if your query screen changes slightly over time, keep the important sections above enabled

## Project Structure

```text
src/ibtaxsp/
  main.py                 FastAPI app
  service.py              application orchestration
  repository.py           yearly file discovery
  models.py               API and domain models
  services/
    flex_parser.py        IB Flex XML parsing
    fifo_engine.py        FIFO matching for securities
    annual_tax.py         annual tax summary
    renta_view.py         filing-oriented summary view
    renta_guidance.py     practical filing guidance
    hacienda_view.py      "what to enter" operational view
    cash_flow_view.py     deposit/withdrawal reading
    simulation.py         non-persistent withdrawal simulation

web/
  src/App.tsx             React frontend
  src/style.css           UI styling
```

## Run Locally

### Backend

```bash
python -m pip install -e .
python -m uvicorn ibtaxsp.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

Then open:

- `http://127.0.0.1:5173/`

## Main API Endpoints

- `GET /api/health`
- `GET /api/years`
- `GET /api/overview`
- `GET /api/year/{year}`
- `GET /api/year/{year}/dataset`
- `GET /api/year/{year}/fifo`
- `GET /api/year/{year}/tax-summary?lang=es|en`
- `GET /api/year/{year}/renta-view?lang=es|en`
- `GET /api/year/{year}/renta-guidance?lang=es|en`
- `GET /api/year/{year}/hacienda-view?lang=es|en`
- `GET /api/year/{year}/cash-flow?lang=es|en`
- `POST /api/simulate/withdrawal`

Example payload:

```json
{
  "year": 2025,
  "amount": 10000,
  "currency": "USD",
  "lang": "en"
}
```

## Typical Workflow

1. Export one `ibtax_full.xml` file per year from IB.
2. Place each file in its year folder under `IB/Tax`.
3. Start backend and frontend.
4. Review yearly summary and filing views.
5. Inspect the FIFO report for audit support.
6. Check dividends, withholdings, and cash flow.
7. Use the withdrawal simulation for scenario testing without changing imported history.

## Current Scope And Limitations

- FIFO support is focused on long stock positions.
- Unsupported operations such as short-sale cases are listed separately and should be reviewed manually.
- If positions existed before the first available imported year, the app seeds opening lots from the first available opening positions.
- Historical completeness depends on the quality and continuity of the yearly IB exports you provide.
- Final tax filing should still be reviewed carefully, especially in complex cases.

## Suggested Next Improvements

- add date-specific simulations instead of year-end-only simulations
- improve support for more complex FX realization chains
- expand unsupported trading patterns
- add anonymized demo data for public repository use
- add tests around fiscal edge cases
