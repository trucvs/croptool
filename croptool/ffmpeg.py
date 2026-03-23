from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover - dependency is documented in requirements.txt
    imageio_ffmpeg = None

from .constants import PREVIEW_HEIGHT, PREVIEW_WIDTH
from .models import CropRegion, VideoMetadata


def resolve_ffmpeg_path() -> Optional[str]:
    if imageio_ffmpeg is None:
        return None

    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def probe_video(ffmpeg_path: str, path: Path) -> VideoMetadata:
    command = [ffmpeg_path, "-hide_banner", "-i", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    payload = (result.stderr or "") + "\n" + (result.stdout or "")

    if "No such file or directory" in payload:
        raise RuntimeError("Khong mo duoc file input.")

    duration_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", payload)
    duration_seconds: Optional[float] = None
    if duration_match:
        hours = int(duration_match.group(1))
        minutes = int(duration_match.group(2))
        seconds = float(duration_match.group(3))
        duration_seconds = (hours * 3600) + (minutes * 60) + seconds

    video_line = None
    for line in payload.splitlines():
        if "Video:" in line:
            video_line = line.strip()
            break

    if not video_line:
        raise RuntimeError("Khong tim thay video stream trong file da chon.")

    codec_match = re.search(r"Video:\s*([^,]+)", video_line)
    codec_name = codec_match.group(1).strip() if codec_match else "unknown"

    dimension_match = re.search(r"(\d{2,5})x(\d{2,5})", video_line)
    if not dimension_match:
        raise RuntimeError("Khong doc duoc kich thuoc frame tu video.")
    width = int(dimension_match.group(1))
    height = int(dimension_match.group(2))

    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", video_line)
    frame_rate = fps_match.group(1) if fps_match else "Unknown"

    return VideoMetadata(
        path=path,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        codec_name=codec_name,
        frame_rate=frame_rate,
    )


def build_preview_command(ffmpeg_path: str, metadata: VideoMetadata, preview_path: Path) -> list[str]:
    seek_seconds = min(metadata.duration_seconds or 0.0, 1.0)
    return [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{seek_seconds:.2f}",
        "-i",
        str(metadata.path),
        "-frames:v",
        "1",
        "-vf",
        f"scale={PREVIEW_WIDTH}:{PREVIEW_HEIGHT}:force_original_aspect_ratio=decrease",
        str(preview_path),
    ]


def build_crop_command(
    ffmpeg_path: str,
    input_path: Path,
    output_path: Path,
    crop: CropRegion,
) -> list[str]:
    crop_filter = f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}"
    return [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        crop_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]


def parse_ffmpeg_timestamp(value: str) -> float:
    try:
        hours_text, minutes_text, seconds_text = value.split(":")
        hours = int(hours_text)
        minutes = int(minutes_text)
        seconds = float(seconds_text)
    except ValueError:
        return 0.0
    return (hours * 3600) + (minutes * 60) + seconds
