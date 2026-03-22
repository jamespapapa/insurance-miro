from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..config import get_project_paths


@dataclass(frozen=True)
class SampleAsset:
    category: str
    path: Path
    relative_path: str
    size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
        }


def collect_sample_assets() -> list[SampleAsset]:
    data_dir = get_project_paths().data_sample
    assets: list[SampleAsset] = []

    if not data_dir.exists():
        return assets

    for category_dir in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        for path in sorted(p for p in category_dir.rglob("*") if p.is_file()):
            assets.append(
                SampleAsset(
                    category=category_dir.name,
                    path=path,
                    relative_path=path.relative_to(data_dir).as_posix(),
                    size_bytes=path.stat().st_size,
                )
            )

    return assets


def summarize_assets(assets: Iterable[SampleAsset]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for asset in assets:
        bucket = summary.setdefault(asset.category, {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += asset.size_bytes
    return summary
