from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class VideoMetadata:
    path: Path
    width: int
    height: int
    duration_seconds: Optional[float]
    codec_name: str
    frame_rate: str


@dataclass(frozen=True)
class CropRegion:
    x: int
    y: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height
