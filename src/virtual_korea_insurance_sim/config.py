from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    docs: Path
    data_sample: Path
    reference_mirofish: Path


def get_project_paths() -> ProjectPaths:
    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(
        root=root,
        docs=root / "docs" / "virtual-korea-insurance-sim",
        data_sample=root / "data-sample",
        reference_mirofish=root / "reference" / "MiroFish",
    )
