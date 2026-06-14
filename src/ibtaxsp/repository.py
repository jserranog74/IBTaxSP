from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaxYearFile:
    year: int
    xml_path: Path


class TaxDataRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list_year_files(self) -> list[TaxYearFile]:
        tax_root = self.root / "IB" / "Tax"
        result: list[TaxYearFile] = []

        if not tax_root.exists():
            return result

        for year_dir in sorted(tax_root.iterdir()):
            if not year_dir.is_dir():
                continue
            if not year_dir.name.isdigit():
                continue

            xml_path = year_dir / "ibtax_full.xml"
            if xml_path.exists():
                result.append(TaxYearFile(year=int(year_dir.name), xml_path=xml_path))

        return result

    def get_year_file(self, year: int) -> TaxYearFile | None:
        for year_file in self.list_year_files():
            if year_file.year == year:
                return year_file
        return None
