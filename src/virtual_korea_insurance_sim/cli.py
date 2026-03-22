from __future__ import annotations

import argparse
from textwrap import indent

from .config import get_project_paths
from .evaluation import phase0_kpi_definitions
from .ingestion import collect_sample_assets, summarize_assets
from .simulation import MarketSimulationEngine
from .synthesis import SyntheticPopulationPlanner


def _build_summary_text() -> str:
    paths = get_project_paths()
    assets = collect_sample_assets()
    summary = summarize_assets(assets)
    engine = MarketSimulationEngine()
    prep = engine.prepare(assets)
    planner = SyntheticPopulationPlanner()

    lines = [
        "miromiro setup summary",
        f"- root: {paths.root}",
        f"- docs: {paths.docs}",
        f"- data-sample: {paths.data_sample}",
        f"- reference/MiroFish exists: {paths.reference_mirofish.exists()}",
        "",
        "sample inventory:",
    ]

    for category, stats in sorted(summary.items()):
        lines.append(f"- {category}: {stats['files']} files, {stats['bytes']} bytes")

    lines.extend(
        [
            "",
            "simulation preparation:",
            f"- required categories: {', '.join(prep.required_categories)}",
            f"- available categories: {', '.join(prep.available_categories) if prep.available_categories else '(none)'}",
            f"- missing categories: {', '.join(prep.missing_categories) if prep.missing_categories else '(none)'}",
            "",
            "synthetic population required dimensions:",
            indent("\n".join(f"- {item}" for item in planner.required_dimensions()), ""),
            "",
            "phase0 KPI targets:",
            indent(
                "\n".join(f"- {kpi.name}: {kpi.description}" for kpi in phase0_kpi_definitions()),
                "",
            ),
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Virtual Korea Insurance Simulation scaffold")
    parser.add_argument(
        "command",
        nargs="?",
        default="summary",
        choices=["summary"],
        help="Command to run",
    )
    args = parser.parse_args()

    if args.command == "summary":
        print(_build_summary_text())
