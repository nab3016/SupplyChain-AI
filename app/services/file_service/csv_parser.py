"""
app/services/file_service/csv_parser.py
Parses uploaded CSV files into a list of ShipmentRecord objects.
Handles encoding issues, missing columns, and type coercion gracefully.
"""

import io
import pandas as pd
from typing import List, Tuple
from app.models.shipment_model import ShipmentRecord
from app.utils.validators import validate_csv_columns
from app.utils.logger import get_logger

logger = get_logger("file_service")

REQUIRED_COLUMNS = [
    "origin",
    "destination",
    "supplier_name",
    "distance_km",
    "shipment_value",
    "delivery_deadline",
]


def parse_shipment_csv(file_bytes: bytes) -> Tuple[List[ShipmentRecord], List[str]]:
    """
    Parse raw CSV bytes into a list of ShipmentRecord Pydantic objects.

    Args:
        file_bytes: Raw bytes of the uploaded CSV file.

    Returns:
        (records: List[ShipmentRecord], errors: List[str])
        errors is empty on full success; partial success returns valid records + error list.
    """
    errors: List[str] = []
    records: List[ShipmentRecord] = []

    try:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
        except Exception as e:
            return [], [f"Failed to read CSV: {e}"]
    except Exception as e:
        return [], [f"Failed to parse CSV: {e}"]

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Validate required columns
    is_valid, err = validate_csv_columns(list(df.columns), REQUIRED_COLUMNS)
    if not is_valid:
        return [], [err]

    df = df.where(pd.notnull(df), None)  # Replace NaN with None

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-indexed + header row
        try:
            record = ShipmentRecord(
                shipment_id=str(row.get("shipment_id", f"CSV-{row_num:04d}")),
                origin=str(row["origin"]),
                destination=str(row["destination"]),
                supplier_name=str(row["supplier_name"]),
                distance_km=float(row["distance_km"]),
                shipment_value=float(row["shipment_value"]),
                delivery_deadline=str(row["delivery_deadline"]),
                priority=str(row.get("priority", "STANDARD")).upper(),
            )
            records.append(record)
        except Exception as e:
            errors.append(f"Row {row_num}: {e}")

    logger.info(f"CSV parsed | {len(records)} valid records | {len(errors)} errors")
    return records, errors
