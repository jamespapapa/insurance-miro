from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KpiDefinition:
    name: str
    description: str


def phase0_kpi_definitions() -> list[KpiDefinition]:
    return [
        KpiDefinition("subscriptions", "예상 신규 계약 수"),
        KpiDefinition("conversion_rate", "노출 대비 가입 전환율"),
        KpiDefinition("channel_contracts", "채널별 계약 수"),
        KpiDefinition("persistency_rate", "유지율 / 잔존율"),
        KpiDefinition("churn_rate", "해지/실효율"),
        KpiDefinition("loss_ratio_proxy", "손해율 proxy"),
        KpiDefinition("profitability_proxy", "수익성 proxy"),
    ]
