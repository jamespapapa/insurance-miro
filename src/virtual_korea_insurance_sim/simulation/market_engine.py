from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..ingestion import SampleAsset


@dataclass(frozen=True)
class MarketSimulationPreparation:
    required_categories: tuple[str, ...]
    available_categories: tuple[str, ...]
    missing_categories: tuple[str, ...]


class MarketSimulationEngine:
    REQUIRED_SAMPLE_CATEGORIES = (
        "population-household",
        "health-risk",
        "insurance-market",
        "channel-digital",
        "macro-regulatory",
    )

    def prepare(self, assets: Iterable[SampleAsset]) -> MarketSimulationPreparation:
        available = sorted({asset.category for asset in assets})
        missing = sorted(set(self.REQUIRED_SAMPLE_CATEGORIES) - set(available))
        return MarketSimulationPreparation(
            required_categories=self.REQUIRED_SAMPLE_CATEGORIES,
            available_categories=tuple(available),
            missing_categories=tuple(missing),
        )

    def run(self) -> None:
        raise NotImplementedError(
            "Monthly insurance market loop is not implemented yet. "
            "Build ingestion + synthetic population first."
        )
