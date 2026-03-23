from pathlib import Path
import unittest

from croptool.ffmpeg import build_crop_command, parse_ffmpeg_timestamp
from croptool.logic import (
    apply_ratio_preset,
    build_crop_summary,
    format_duration,
    suggest_output_path,
    validate_crop,
)
from croptool.models import VideoMetadata


class CropLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = VideoMetadata(
            path=Path("sample.mp4"),
            width=1920,
            height=1080,
            duration_seconds=65.4,
            codec_name="h264",
            frame_rate="30",
        )

    def test_suggest_output_path_keeps_supported_suffix(self) -> None:
        result = suggest_output_path(Path("clip.mov"))
        self.assertEqual(result, Path("clip_cropped.mov"))

    def test_suggest_output_path_falls_back_to_mp4(self) -> None:
        result = suggest_output_path(Path("clip.weird"))
        self.assertEqual(result, Path("clip_cropped.mp4"))

    def test_format_duration_handles_hours(self) -> None:
        self.assertEqual(format_duration(3723), "01:02:03")

    def test_validate_crop_rejects_odd_dimensions_for_export(self) -> None:
        with self.assertRaisesRegex(ValueError, "so chan"):
            validate_crop(self.metadata, x=0, y=0, width=1279, height=720, strict=True)

    def test_build_crop_summary_mentions_even_constraint_when_invalid(self) -> None:
        summary = build_crop_summary(self.metadata, None)
        self.assertIn("so chan", summary)

    def test_apply_ratio_preset_returns_even_dimensions(self) -> None:
        odd_metadata = VideoMetadata(
            path=Path("odd.mp4"),
            width=1001,
            height=1001,
            duration_seconds=None,
            codec_name="h264",
            frame_rate="30",
        )

        crop = apply_ratio_preset(odd_metadata, "16:9")
        self.assertEqual(crop.width % 2, 0)
        self.assertEqual(crop.height % 2, 0)
        self.assertLessEqual(crop.x + crop.width, odd_metadata.width)
        self.assertLessEqual(crop.y + crop.height, odd_metadata.height)

    def test_build_crop_command_contains_expected_filter(self) -> None:
        crop = validate_crop(self.metadata, x=100, y=20, width=1280, height=720, strict=True)
        assert crop is not None
        command = build_crop_command("ffmpeg.exe", Path("in.mp4"), Path("out.mp4"), crop)
        self.assertIn("crop=1280:720:100:20", command)
        self.assertEqual(command[-1], "out.mp4")

    def test_parse_ffmpeg_timestamp(self) -> None:
        self.assertEqual(parse_ffmpeg_timestamp("01:02:03.5"), 3723.5)


if __name__ == "__main__":
    unittest.main()
