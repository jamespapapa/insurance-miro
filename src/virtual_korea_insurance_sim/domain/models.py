from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HouseholdSegment:
    segment_id: str
    region: str
    age_band: str
    household_type: str
    income_band: str
    health_risk_bucket: str
    digital_affinity: float
    channel_preference: str
    monthly_budget_headroom: float
    population_weight: int


@dataclass(frozen=True)
class InsuranceProduct:
    product_id: str
    carrier_name: str
    product_type: str
    premium_index: float
    coverage_index: float
    underwriting_strictness: float
    target_segments: tuple[str, ...] = ()


@dataclass(frozen=True)
class CarrierProfile:
    carrier_name: str
    brand_strength: float
    channel_mix: tuple[str, ...]
    pricing_strategy: str
    notes: str = ""


@dataclass(frozen=True)
class ChannelProfile:
    channel_id: str
    channel_type: str
    trust_level: float
    acquisition_cost_index: float
    persistency_quality: float


@dataclass(frozen=True)
class MacroScenario:
    scenario_id: str
    interest_rate_regime: str
    inflation_regime: str
    unemployment_regime: str
    regulation_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProductExperimentScenario:
    scenario_id: str
    product: InsuranceProduct
    carrier: CarrierProfile
    channels: tuple[ChannelProfile, ...]
    macro: MacroScenario
    horizon_months: int = 12
    notes: tuple[str, ...] = field(default_factory=tuple)
