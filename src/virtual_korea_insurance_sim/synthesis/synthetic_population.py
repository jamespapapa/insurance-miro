from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticPopulationConfig:
    region_granularity: str = "sido"
    target_household_segments: int = 10000
    use_health_risk_proxy: bool = True
    use_digital_affinity_proxy: bool = True
    use_affordability_proxy: bool = True


class SyntheticPopulationPlanner:
    """Phase 0 설계용 planner.

    아직 실제 synthetic household를 생성하진 않지만,
    구현 전에 반드시 채워야 할 feature 축과 우선순위를 고정한다.
    """

    def __init__(self, config: SyntheticPopulationConfig | None = None):
        self.config = config or SyntheticPopulationConfig()

    def required_dimensions(self) -> list[str]:
        return [
            "region",
            "age_band",
            "household_type",
            "income_band",
            "health_risk_bucket",
            "digital_affinity",
            "channel_preference",
            "monthly_budget_headroom",
        ]

    def phase0_todo(self) -> list[str]:
        return [
            "Parse MOIS population/household sample",
            "Add regional health risk proxy from KDCA sample",
            "Add channel/digital proxy from KISA sample",
            "Add affordability proxy from BOK + household statistics",
            "Output household segment table for simulation input",
        ]
