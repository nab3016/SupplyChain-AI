"""
app/utils/validators.py
Input validation helpers used by API routes and agents.
"""

from datetime import date
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger("validators")


def validate_shipment_input(
    origin: str,
    destination: str,
    supplier_name: str,
    distance_km: float,
    shipment_value: float,
    delivery_deadline: date,
) -> tuple[bool, Optional[str]]:
    """
    Validate raw shipment input fields.

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not origin or len(origin.strip()) < 2:
        return False, "Origin must be at least 2 characters."

    if not destination or len(destination.strip()) < 2:
        return False, "Destination must be at least 2 characters."

    if origin.strip().lower() == destination.strip().lower():
        return False, "Origin and destination cannot be the same."

    if not supplier_name or len(supplier_name.strip()) < 2:
        return False, "Supplier name must be at least 2 characters."

    if distance_km <= 0:
        return False, "Distance must be a positive number."

    if distance_km > 50000:
        return False, "Distance exceeds maximum allowed value (50,000 km)."

    if shipment_value <= 0:
        return False, "Shipment value must be a positive number."

    if delivery_deadline < date.today():
        return False, "Delivery deadline cannot be in the past."

    logger.debug(f"Shipment input validated: {origin} → {destination}")
    return True, None


def validate_csv_columns(df_columns: list[str], required: list[str]) -> tuple[bool, Optional[str]]:
    """
    Check that a parsed CSV DataFrame contains all required columns.

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    missing = [col for col in required if col not in df_columns]
    if missing:
        return False, f"CSV is missing required columns: {missing}"
    return True, None
