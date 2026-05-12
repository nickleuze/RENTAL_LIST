#!/usr/bin/env python3
"""Convert the public rental inventory from Rental-Database.xlsm to JSON.

Uses only Python's standard library so the project has no install step.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from zipfile import ZipFile
from xml.etree import ElementTree as ET

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

DEFAULT_INPUT = Path(os.environ.get("INVENTORY_XLSM", "Rental-Database.xlsm"))
DEFAULT_OUTPUT = Path("data/inventory.json")
PUBLIC_SHEET = "Rental-Database"

HEADER_MAP = {
    "Artikelnummer": "sku",
    "Menge": "quantity",
    "Bezeichnung": "name",
    "Beschreibung": "description",
    "Notiz": "category",
    "Einheit": "unit",
    "VK (Netto)": "price_net",
}
REQUIRED_FIELDS = {
    "sku": "Artikelnummer",
    "name": "Bezeichnung",
    "category": "Notiz",
    "price_net": "VK (Netto)",
}


@dataclass
class InventoryItem:
    sku: str
    quantity: int | str
    name: str
    description: str
    category: str
    unit: str
    price_net: float | int | str | None


def load_shared_strings(zf: ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings: List[str] = []
    for si in root.findall("main:si", NS):
        strings.append("".join(t.text or "" for t in si.iter(f"{MAIN_NS}t")))
    return strings


def cell_value(cell: ET.Element, shared_strings: List[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{MAIN_NS}t")).strip()

    value = cell.find("main:v", NS)
    if value is None or value.text is None:
        return ""

    raw = value.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(raw)].strip()
        except (ValueError, IndexError):
            return raw
    return raw


def column_name(cell_ref: str) -> str:
    match = re.match(r"([A-Z]+)", cell_ref)
    return match.group(1) if match else ""


def normalize_number(value: str) -> int | float | str | None:
    if value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return int(number)
    return number


def normalize_quantity(value: str) -> int | str:
    number = normalize_number(value)
    if number is None:
        return 1
    return number


def workbook_sheets(zf: ZipFile) -> Dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}

    sheets: Dict[str, str] = {}
    sheets_element = workbook.find("main:sheets", NS)
    if sheets_element is None:
        return sheets
    for sheet in sheets_element:
        rel_id = sheet.attrib[f"{REL_NS}id"]
        target = rel_targets[rel_id]
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        sheets[sheet.attrib["name"]] = target
    return sheets


def worksheet_rows(zf: ZipFile, sheet_path: str, shared_strings: List[str]) -> Iterable[Tuple[int, Dict[str, str]]]:
    root = ET.fromstring(zf.read(sheet_path))
    for row in root.findall(".//main:sheetData/main:row", NS):
        row_number = int(row.attrib["r"])
        values: Dict[str, str] = {}
        for cell in row.findall("main:c", NS):
            col = column_name(cell.attrib.get("r", ""))
            if col:
                values[col] = cell_value(cell, shared_strings)
        yield row_number, values


def convert_inventory(input_path: Path) -> dict:
    with ZipFile(input_path) as zf:
        shared_strings = load_shared_strings(zf)
        sheets = workbook_sheets(zf)
        if PUBLIC_SHEET not in sheets:
            raise ValueError(f"Missing expected sheet: {PUBLIC_SHEET!r}")

        rows = list(worksheet_rows(zf, sheets[PUBLIC_SHEET], shared_strings))

    if not rows:
        raise ValueError("Inventory sheet is empty")

    _, header_row = rows[0]
    columns = {col: HEADER_MAP[label] for col, label in header_row.items() if label in HEADER_MAP}
    column_by_field = {field: col for col, field in columns.items()}
    missing_headers = [label for field, label in REQUIRED_FIELDS.items() if field not in column_by_field]
    if missing_headers:
        raise ValueError(f"Missing required header(s): {', '.join(missing_headers)}")

    items: List[InventoryItem] = []
    sku_col = column_by_field["sku"]
    name_col = column_by_field["name"]
    current_section = "Uncategorized"
    for _, row in rows[1:]:
        sku = row.get(sku_col, "").strip()
        name = row.get(name_col, "").strip()
        if not sku:
            # Rows with a name but no SKU are section headings in the workbook.
            # Use them as the public category names instead of the shorter Notiz codes.
            if name:
                current_section = name
            continue
        if not name:
            # Incomplete item row; skip until the workbook has a display name.
            continue

        item_data = {field: "" for field in HEADER_MAP.values()}
        for field, col in column_by_field.items():
            item_data[field] = row.get(col, "").strip()

        items.append(
            InventoryItem(
                sku=item_data["sku"],
                quantity=normalize_quantity(item_data["quantity"]),
                name=item_data["name"],
                description=item_data["description"],
                category=current_section or item_data["category"] or "Uncategorized",
                unit=item_data["unit"] or "Day(s)",
                price_net=normalize_number(item_data["price_net"]),
            )
        )

    categories = sorted({item.category for item in items})
    return {
        "source": input_path.name,
        "sheet": PUBLIC_SHEET,
        "publicPricing": "VK (Netto)",
        "itemCount": len(items),
        "categories": categories,
        "items": [asdict(item) for item in items],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Rental-Database.xlsm to public catalog JSON")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Validate conversion without writing the output file")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Missing input workbook: {args.input}", file=sys.stderr)
        return 1

    data = convert_inventory(args.input)
    if args.check:
        print(f"OK: {data['itemCount']} items from {data['sheet']} ({len(data['categories'])} categories)")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.output} with {data['itemCount']} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
