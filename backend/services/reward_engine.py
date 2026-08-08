"""Deterministic, unit-testable reward rules for every SmartSeg waste event."""
from __future__ import annotations

CATEGORY_FACTORS = {"PLASTIC": 1.5, "METAL": 2.0, "ORGANIC": 1.0, "OTHER": 0.5}


def calculate_reward(category: str, weight_grams: float | None, confidence_score: float | None) -> int:
    """Return integer points; uncertain classifications earn half the normal reward."""
    base_points = max(0, int((weight_grams or 0) // 10))
    points = base_points * CATEGORY_FACTORS.get(category.upper(), CATEGORY_FACTORS["OTHER"])
    if confidence_score is None or confidence_score < 0.6:
        points *= 0.5
    return int(points)
