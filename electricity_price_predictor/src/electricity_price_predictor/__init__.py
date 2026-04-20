"""Electricity price forecasting data pipeline package."""

from .db import get_engine

__all__ = ["EntsoeDataService", "build_feature_frame", "get_engine"]


def __getattr__(name: str):
    if name == "EntsoeDataService":
        from .entsoe_api import EntsoeDataService

        return EntsoeDataService
    if name == "build_feature_frame":
        from .features import build_feature_frame

        return build_feature_frame
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
