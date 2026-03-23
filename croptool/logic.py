from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from .constants import PRESET_RATIOS, SUPPORTED_OUTPUT_SUFFIXES
from .models import CropRegion, VideoMetadata


def suggest_output_path(input_path: Path) -> Path:
    suffix = input_path.suffix.lower() if input_path.suffix else ".mp4"
    if suffix not in SUPPORTED_OUTPUT_SUFFIXES:
        suffix = ".mp4"
    return input_path.with_name(f"{input_path.stem}_cropped{suffix}")


def format_duration(duration_seconds: Optional[float]) -> str:
    if duration_seconds is None:
        return "Unknown"

    minutes, seconds = divmod(int(duration_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def validate_crop(
    metadata: Optional[VideoMetadata],
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    strict: bool,
) -> Optional[CropRegion]:
    if metadata is None:
        return None

    if width <= 0 or height <= 0:
        if strict:
            raise ValueError("Width va height phai lon hon 0.")
        return None

    if x < 0 or y < 0:
        if strict:
            raise ValueError("X va Y khong duoc am.")
        return None

    if x + width > metadata.width or y + height > metadata.height:
        if strict:
            raise ValueError("Vung crop dang vuot qua kich thuoc frame goc.")
        return None

    if width % 2 != 0 or height % 2 != 0:
        if strict:
            raise ValueError("Width va height phai la so chan de xuat voi libx264/yuv420p.")
        return None

    return CropRegion(x=x, y=y, width=width, height=height)


def center_crop(metadata: VideoMetadata, crop: CropRegion) -> CropRegion:
    centered_x = max((metadata.width - crop.width) // 2, 0)
    centered_y = max((metadata.height - crop.height) // 2, 0)
    return CropRegion(
        x=centered_x,
        y=centered_y,
        width=crop.width,
        height=crop.height,
    )


def apply_ratio_preset(metadata: VideoMetadata, ratio_key: str) -> CropRegion:
    ratio = PRESET_RATIOS.get(ratio_key)
    if ratio is None:
        raise KeyError(f"Unknown ratio preset: {ratio_key}")

    ratio_width, ratio_height = ratio
    source_ratio = metadata.width / metadata.height
    target_ratio = ratio_width / ratio_height

    if source_ratio > target_ratio:
        crop_height = metadata.height
        crop_width = int(math.floor(crop_height * target_ratio))
    else:
        crop_width = metadata.width
        crop_height = int(math.floor(crop_width / target_ratio))

    crop_width = _make_even_down(min(crop_width, metadata.width))
    crop_height = _make_even_down(min(crop_height, metadata.height))

    if crop_width <= 0 or crop_height <= 0:
        raise ValueError("Khong tao duoc crop hop le cho preset da chon.")

    crop_x = max((metadata.width - crop_width) // 2, 0)
    crop_y = max((metadata.height - crop_height) // 2, 0)
    return CropRegion(x=crop_x, y=crop_y, width=crop_width, height=crop_height)


def build_source_info(metadata: Optional[VideoMetadata]) -> str:
    if metadata is None:
        return "Chua tai video."

    return "\n".join(
        [
            f"File: {metadata.path.name}",
            f"Resolution: {metadata.width} x {metadata.height}",
            f"Duration: {format_duration(metadata.duration_seconds)}",
            f"Codec: {metadata.codec_name}",
            f"FPS: {metadata.frame_rate}",
        ]
    )


def build_crop_summary(metadata: Optional[VideoMetadata], crop: Optional[CropRegion]) -> str:
    if metadata is None:
        return "Tai video truoc de xem thong tin crop."

    if crop is None:
        return (
            f"Nhap x, y, width, height hop le nam trong frame "
            f"{metadata.width}x{metadata.height}, voi width/height la so chan."
        )

    return (
        f"Crop {crop.width}x{crop.height} tai ({crop.x}, {crop.y}) | "
        f"Output frame: {crop.width}x{crop.height}"
    )


def _make_even_down(value: int) -> int:
    if value % 2 == 0:
        return value
    return value - 1
