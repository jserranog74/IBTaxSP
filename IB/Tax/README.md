Place your private Interactive Brokers yearly exports here.

Recommended structure:

- `IB/Tax/2023/ibtax_full.xml`
- `IB/Tax/2024/ibtax_full.xml`
- `IB/Tax/2025/ibtax_full.xml`

Expected source:

- Interactive Brokers `Activity Flex Query`
- `Format: XML`
- one file per year
- file name: `ibtax_full.xml`

Important sections to export:

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

Recommended export options:

- `Include currency rates: Yes`
- `Include audit trail fields: Yes`
- `Include offsetting trade/cancel pairs: Yes`

This folder is intentionally ignored by Git except for this placeholder file.
