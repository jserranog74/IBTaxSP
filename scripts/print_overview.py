from __future__ import annotations

from pathlib import Path
import json

from ibtaxsp.service import TaxService


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    service = TaxService(root)
    print(json.dumps(service.get_overview().model_dump(), indent=2))


if __name__ == "__main__":
    main()
