from __future__ import annotations

import queue
import shlex
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

import dearpygui.dearpygui as dpg

from .constants import MODAL_TAG, PRESET_RATIOS, PREVIEW_HEIGHT, PREVIEW_WIDTH
from .ffmpeg import (
    build_crop_command,
    build_preview_command,
    parse_ffmpeg_timestamp,
    probe_video,
    resolve_ffmpeg_path,
)
from .logic import (
    apply_ratio_preset,
    build_crop_summary,
    build_source_info,
    center_crop,
    suggest_output_path,
    validate_crop,
)
from .models import CropRegion, VideoMetadata


def _largest_even(value: int) -> int:
    return value if value % 2 == 0 else value - 1


class VideoCropApp:
    def __init__(self) -> None:
        self.ffmpeg_path = resolve_ffmpeg_path()
        self.metadata: Optional[VideoMetadata] = None
        self.message_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.current_process: Optional[subprocess.Popen[str]] = None

        self.preview_temp_path: Optional[Path] = None
        self.preview_texture_tag = "preview_texture"
        self.preview_texture_size = (0, 0)

        self.tags = {
            "main_window": "main_window",
            "input_dialog": "input_dialog",
            "output_dir_dialog": "output_dir_dialog",
            "input_path": "input_path",
            "output_path": "output_path",
            "source_info": "source_info",
            "crop_x": "crop_x",
            "crop_y": "crop_y",
            "crop_width": "crop_width",
            "crop_height": "crop_height",
            "ratio_combo": "ratio_combo",
            "crop_summary": "crop_summary",
            "status_text": "status_text",
            "preview_hint": "preview_hint",
            "progress_bar": "progress_bar",
            "progress_text": "progress_text",
            "log_output": "log_output",
            "preview_drawlist": "preview_drawlist",
            "texture_registry": "texture_registry",
            "dependency_text": "dependency_text",
        }

        self.interactive_tags = [
            self.tags["input_path"],
            self.tags["output_path"],
            self.tags["crop_x"],
            self.tags["crop_y"],
            self.tags["crop_width"],
            self.tags["crop_height"],
            self.tags["ratio_combo"],
            "browse_input_button",
            "load_video_button",
            "browse_output_button",
            "apply_ratio_button",
            "full_frame_button",
            "center_crop_button",
            "run_button",
        ]

        dpg.create_context()
        self._build_theme()
        self._build_ui()

    def _build_theme(self) -> None:
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 10)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 16)
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (239, 244, 248, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (255, 255, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (255, 255, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (245, 247, 250, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (226, 232, 240, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (209, 219, 230, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 118, 110, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (17, 94, 89, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (19, 78, 74, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Header, (226, 232, 240, 255))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (203, 213, 225, 255))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (148, 163, 184, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (215, 222, 232, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (15, 23, 42, 255))
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (249, 115, 22, 255))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (249, 115, 22, 255))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (234, 88, 12, 255))

        dpg.bind_theme(global_theme)

    def _build_ui(self) -> None:
        with dpg.texture_registry(show=False, tag=self.tags["texture_registry"]):
            pass

        self._build_file_dialogs()

        with dpg.window(tag=self.tags["main_window"], label="Video Crop Studio"):
            dpg.add_text("Video Crop Studio")
            dpg.add_text(
                "Cong cu Python de crop spatial dimensions cho video voi preview va xuat bang FFmpeg nhung san."
            )
            dpg.add_spacer(height=6)

            with dpg.group(horizontal=True):
                self._build_left_panel()
                self._build_right_panel()

        self._update_dependency_banner()
        self._refresh_source_info()
        self._set_preview_hint("Chon video de tai metadata va hien thi preview crop.")
        self._set_status("San sang.")
        self._set_log("")
        self._update_crop_summary()

    def _build_file_dialogs(self) -> None:
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._on_input_file_selected,
            tag=self.tags["input_dialog"],
            width=700,
            height=420,
            modal=True,
        ):
            dpg.add_file_extension(".*")
            dpg.add_file_extension(".mp4", color=(34, 197, 94, 255))
            dpg.add_file_extension(".mov", color=(34, 197, 94, 255))
            dpg.add_file_extension(".mkv", color=(34, 197, 94, 255))
            dpg.add_file_extension(".avi", color=(34, 197, 94, 255))
            dpg.add_file_extension(".m4v", color=(34, 197, 94, 255))
            dpg.add_file_extension(".webm", color=(34, 197, 94, 255))

        with dpg.file_dialog(
            directory_selector=True,
            show=False,
            callback=self._on_output_dir_selected,
            tag=self.tags["output_dir_dialog"],
            width=700,
            height=420,
            modal=True,
        ):
            pass

    def _build_left_panel(self) -> None:
        with dpg.child_window(width=390, autosize_y=True, border=False):
            dpg.add_text("Trang thai he thong")
            dpg.add_text("", tag=self.tags["dependency_text"], wrap=350)
            dpg.add_separator()

            dpg.add_text("Tap tin")
            dpg.add_input_text(label="Video input", width=-1, tag=self.tags["input_path"])
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Chon video",
                    callback=lambda: dpg.show_item(self.tags["input_dialog"]),
                    tag="browse_input_button",
                )
                dpg.add_button(label="Tai video", callback=self._load_video_from_input, tag="load_video_button")

            dpg.add_input_text(label="Video output", width=-1, tag=self.tags["output_path"])
            dpg.add_button(
                label="Chon thu muc output",
                callback=lambda: dpg.show_item(self.tags["output_dir_dialog"]),
                tag="browse_output_button",
            )

            dpg.add_separator()
            dpg.add_text("Thong tin nguon")
            dpg.add_text("", tag=self.tags["source_info"], wrap=350)

            dpg.add_separator()
            dpg.add_text("Thiet lap crop")
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    label="X",
                    width=160,
                    tag=self.tags["crop_x"],
                    default_value=0,
                    callback=self._on_crop_changed,
                )
                dpg.add_input_int(
                    label="Y",
                    width=160,
                    tag=self.tags["crop_y"],
                    default_value=0,
                    callback=self._on_crop_changed,
                )
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    label="Width",
                    width=160,
                    tag=self.tags["crop_width"],
                    default_value=0,
                    callback=self._on_crop_changed,
                )
                dpg.add_input_int(
                    label="Height",
                    width=160,
                    tag=self.tags["crop_height"],
                    default_value=0,
                    callback=self._on_crop_changed,
                )

            with dpg.group(horizontal=True):
                dpg.add_combo(
                    items=list(PRESET_RATIOS.keys()),
                    default_value="16:9",
                    width=160,
                    tag=self.tags["ratio_combo"],
                )
                dpg.add_button(label="Ap dung preset", callback=self._apply_ratio_preset, tag="apply_ratio_button")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Full Frame", callback=self._set_full_frame, tag="full_frame_button")
                dpg.add_button(label="Center Crop", callback=self._center_current_crop, tag="center_crop_button")

            dpg.add_text("", tag=self.tags["crop_summary"], wrap=350)

            dpg.add_separator()
            dpg.add_text("Xu ly")
            dpg.add_button(label="Crop va xuat video", callback=self._start_crop, tag="run_button", width=-1, height=40)
            dpg.add_text("", tag=self.tags["status_text"], wrap=350)

    def _build_right_panel(self) -> None:
        with dpg.child_window(width=-1, autosize_y=True, border=False):
            dpg.add_text("Preview")
            dpg.add_text("", tag=self.tags["preview_hint"], wrap=760)
            dpg.add_spacer(height=6)
            dpg.add_drawlist(width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT, tag=self.tags["preview_drawlist"])
            dpg.add_spacer(height=8)
            dpg.add_text("Tien trinh")
            dpg.add_progress_bar(default_value=0.0, width=PREVIEW_WIDTH, tag=self.tags["progress_bar"])
            dpg.add_text("0%", tag=self.tags["progress_text"])
            dpg.add_spacer(height=8)
            with dpg.group(horizontal=True):
                dpg.add_text("Log")
                dpg.add_button(label="Xoa log", callback=lambda: self._set_log(""))
            dpg.add_input_text(
                multiline=True,
                readonly=True,
                width=PREVIEW_WIDTH,
                height=210,
                tag=self.tags["log_output"],
            )
            self._render_preview()

    def _update_dependency_banner(self) -> None:
        if self.ffmpeg_path:
            dpg.set_value(
                self.tags["dependency_text"],
                "FFmpeg da san sang thong qua imageio-ffmpeg. Ban co the crop video ngay trong app.",
            )
            return

        dpg.set_value(
            self.tags["dependency_text"],
            "Khong tim thay FFmpeg nhung san. Hay cai dependencies trong requirements.txt truoc khi xu ly video.",
        )

    def _on_input_file_selected(self, _sender: str, app_data: dict, _user_data: object) -> None:
        selected_path = self._extract_selected_path(app_data)
        if not selected_path:
            return

        input_path = Path(selected_path)
        dpg.set_value(self.tags["input_path"], str(input_path))
        dpg.set_value(self.tags["output_path"], str(suggest_output_path(input_path)))
        self._load_video(input_path)

    def _on_output_dir_selected(self, _sender: str, app_data: dict, _user_data: object) -> None:
        selected_dir = app_data.get("file_path_name") or app_data.get("current_path")
        if not selected_dir:
            return

        input_text = dpg.get_value(self.tags["input_path"]).strip()
        if input_text:
            suggested_name = suggest_output_path(Path(input_text)).name
        else:
            suggested_name = "cropped_output.mp4"
        dpg.set_value(self.tags["output_path"], str(Path(selected_dir) / suggested_name))

    def _extract_selected_path(self, app_data: dict) -> Optional[str]:
        selections = app_data.get("selections") or {}
        if selections:
            return next(iter(selections.values()))
        return app_data.get("file_path_name")

    def _load_video_from_input(self) -> None:
        input_text = dpg.get_value(self.tags["input_path"]).strip()
        if not input_text:
            self._show_modal("Chua co input", "Hay chon mot video input truoc.")
            return
        self._load_video(Path(input_text))

    def _load_video(self, path: Path) -> None:
        if not path.exists():
            self._show_modal("Khong tim thay file", "Video input khong ton tai.")
            return

        if not self.ffmpeg_path:
            self._show_modal(
                "Thieu FFmpeg",
                "Khong tim thay FFmpeg nhung san. Hay cai dependencies truoc khi tai video.",
            )
            return

        try:
            self.metadata = probe_video(self.ffmpeg_path, path)
        except Exception as exc:  # noqa: BLE001
            self.metadata = None
            self._delete_preview_assets()
            self._refresh_source_info()
            self._set_preview_hint("Preview tam thoi khong kha dung.")
            self._set_status("Doc metadata that bai.")
            self._append_log(f"Loi doc metadata: {exc}")
            self._render_preview()
            self._show_modal("Doc metadata that bai", str(exc))
            return

        dpg.set_value(self.tags["crop_x"], 0)
        dpg.set_value(self.tags["crop_y"], 0)
        dpg.set_value(self.tags["crop_width"], _largest_even(self.metadata.width))
        dpg.set_value(self.tags["crop_height"], _largest_even(self.metadata.height))
        self._refresh_source_info()
        self._set_preview_hint("Khung mau cam la vung crop duoc xuat ra.")
        self._set_status("Da tai video. Ban co the canh crop va bat dau xu ly.")
        self._append_log(f"Da tai video: {path.name}")
        self._append_log(
            f"Resolution: {self.metadata.width}x{self.metadata.height} | FPS: {self.metadata.frame_rate}"
        )
        self._refresh_preview_image()
        self._update_crop_summary()
        self._render_preview()

    def _refresh_source_info(self) -> None:
        self._set_source_info(build_source_info(self.metadata))

    def _refresh_preview_image(self) -> None:
        if not self.metadata or not self.ffmpeg_path:
            self._delete_preview_assets()
            self._render_preview()
            return

        self._delete_preview_assets()
        temp_file = tempfile.NamedTemporaryFile(prefix="video_crop_preview_", suffix=".png", delete=False)
        temp_file.close()
        preview_path = Path(temp_file.name)

        command = build_preview_command(self.ffmpeg_path, self.metadata, preview_path)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self._set_preview_hint("Khong tao duoc preview frame tu video.")
            self._append_log(result.stderr.strip() or "Khong tao duoc preview.")
            preview_path.unlink(missing_ok=True)
            return

        try:
            width, height, _channels, data = dpg.load_image(str(preview_path))
        except Exception as exc:  # noqa: BLE001
            preview_path.unlink(missing_ok=True)
            self._append_log(f"Loi tai preview image: {exc}")
            self._set_preview_hint("Khong tai duoc preview image vao giao dien.")
            return

        if dpg.does_item_exist(self.preview_texture_tag):
            dpg.delete_item(self.preview_texture_tag)

        dpg.add_static_texture(
            width,
            height,
            data,
            tag=self.preview_texture_tag,
            parent=self.tags["texture_registry"],
        )
        self.preview_temp_path = preview_path
        self.preview_texture_size = (width, height)

    def _delete_preview_assets(self) -> None:
        if self.preview_temp_path and self.preview_temp_path.exists():
            self.preview_temp_path.unlink(missing_ok=True)
        self.preview_temp_path = None

        if dpg.does_item_exist(self.preview_texture_tag):
            dpg.delete_item(self.preview_texture_tag)
        self.preview_texture_size = (0, 0)

    def _render_preview(self) -> None:
        dpg.delete_item(self.tags["preview_drawlist"], children_only=True)
        dpg.draw_rectangle(
            (0, 0),
            (PREVIEW_WIDTH, PREVIEW_HEIGHT),
            color=(15, 23, 42, 255),
            fill=(15, 23, 42, 255),
            parent=self.tags["preview_drawlist"],
        )

        if not dpg.does_item_exist(self.preview_texture_tag) or not self.metadata:
            dpg.draw_text(
                (130, PREVIEW_HEIGHT / 2 - 12),
                "Preview se xuat hien tai day sau khi tai video.",
                color=(203, 213, 225, 255),
                size=18,
                parent=self.tags["preview_drawlist"],
            )
            return

        image_width, image_height = self.preview_texture_size
        origin_x = max((PREVIEW_WIDTH - image_width) / 2, 0.0)
        origin_y = max((PREVIEW_HEIGHT - image_height) / 2, 0.0)

        dpg.draw_image(
            self.preview_texture_tag,
            (origin_x, origin_y),
            (origin_x + image_width, origin_y + image_height),
            parent=self.tags["preview_drawlist"],
        )

        crop = self._get_crop_values(strict=False)
        if crop is None:
            return

        scale_x = image_width / self.metadata.width
        scale_y = image_height / self.metadata.height

        x1 = origin_x + crop.x * scale_x
        y1 = origin_y + crop.y * scale_y
        x2 = origin_x + (crop.x + crop.width) * scale_x
        y2 = origin_y + (crop.y + crop.height) * scale_y

        shade_fill = (2, 6, 23, 120)
        outline = (249, 115, 22, 255)
        dpg.draw_rectangle(
            (origin_x, origin_y),
            (origin_x + image_width, y1),
            fill=shade_fill,
            color=shade_fill,
            parent=self.tags["preview_drawlist"],
        )
        dpg.draw_rectangle(
            (origin_x, y2),
            (origin_x + image_width, origin_y + image_height),
            fill=shade_fill,
            color=shade_fill,
            parent=self.tags["preview_drawlist"],
        )
        dpg.draw_rectangle(
            (origin_x, y1),
            (x1, y2),
            fill=shade_fill,
            color=shade_fill,
            parent=self.tags["preview_drawlist"],
        )
        dpg.draw_rectangle(
            (x2, y1),
            (origin_x + image_width, y2),
            fill=shade_fill,
            color=shade_fill,
            parent=self.tags["preview_drawlist"],
        )
        dpg.draw_rectangle((x1, y1), (x2, y2), color=outline, thickness=3, parent=self.tags["preview_drawlist"])
        dpg.draw_text(
            (x1 + 10, max(y1 - 24, origin_y + 12)),
            f"{crop.width} x {crop.height}",
            color=(248, 250, 252, 255),
            size=16,
            parent=self.tags["preview_drawlist"],
        )

    def _on_crop_changed(self, _sender: str, _app_data: object, _user_data: object) -> None:
        self._update_crop_summary()
        self._render_preview()

    def _update_crop_summary(self) -> None:
        crop = self._get_crop_values(strict=False)
        self._set_crop_summary(build_crop_summary(self.metadata, crop))

    def _get_crop_values(self, strict: bool) -> Optional[CropRegion]:
        if not self.metadata:
            return None

        return validate_crop(
            self.metadata,
            x=int(dpg.get_value(self.tags["crop_x"])),
            y=int(dpg.get_value(self.tags["crop_y"])),
            width=int(dpg.get_value(self.tags["crop_width"])),
            height=int(dpg.get_value(self.tags["crop_height"])),
            strict=strict,
        )

    def _set_full_frame(self) -> None:
        if not self.metadata:
            return

        dpg.set_value(self.tags["crop_x"], 0)
        dpg.set_value(self.tags["crop_y"], 0)
        dpg.set_value(self.tags["crop_width"], _largest_even(self.metadata.width))
        dpg.set_value(self.tags["crop_height"], _largest_even(self.metadata.height))
        self._update_crop_summary()
        self._render_preview()

    def _center_current_crop(self) -> None:
        if not self.metadata:
            return

        crop = self._get_crop_values(strict=False)
        if crop is None:
            self._set_full_frame()
            crop = self._get_crop_values(strict=False)
            if crop is None:
                return

        centered_crop = center_crop(self.metadata, crop)
        dpg.set_value(self.tags["crop_x"], centered_crop.x)
        dpg.set_value(self.tags["crop_y"], centered_crop.y)
        self._update_crop_summary()
        self._render_preview()

    def _apply_ratio_preset(self) -> None:
        if not self.metadata:
            return

        ratio_key = dpg.get_value(self.tags["ratio_combo"])
        try:
            crop = apply_ratio_preset(self.metadata, ratio_key)
        except ValueError as exc:
            self._show_modal("Preset khong hop le", str(exc))
            return

        dpg.set_value(self.tags["crop_x"], crop.x)
        dpg.set_value(self.tags["crop_y"], crop.y)
        dpg.set_value(self.tags["crop_width"], crop.width)
        dpg.set_value(self.tags["crop_height"], crop.height)
        self._update_crop_summary()
        self._render_preview()

    def _start_crop(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        if not self.ffmpeg_path:
            self._show_modal("Thieu FFmpeg", "Khong tim thay FFmpeg trong moi truong hien tai.")
            return

        if not self.metadata:
            input_text = dpg.get_value(self.tags["input_path"]).strip()
            if not input_text:
                self._show_modal("Chua co input", "Hay chon mot video input truoc.")
                return
            self._load_video(Path(input_text))
            if not self.metadata:
                return

        try:
            crop = self._get_crop_values(strict=True)
        except ValueError as exc:
            self._show_modal("Crop khong hop le", str(exc))
            return

        if crop is None:
            self._show_modal("Crop khong hop le", "Khong the doc gia tri crop hien tai.")
            return

        output_text = dpg.get_value(self.tags["output_path"]).strip()
        if not output_text:
            output_path = suggest_output_path(self.metadata.path)
            dpg.set_value(self.tags["output_path"], str(output_path))
        else:
            output_path = Path(output_text)

        if output_path.resolve() == self.metadata.path.resolve():
            self._show_modal("Output khong hop le", "Video output khong duoc trung voi input.")
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = build_crop_command(self.ffmpeg_path, self.metadata.path, output_path, crop)

        self._set_progress(0.0)
        self._set_status("Dang crop video...")
        self._set_processing_state(True)
        self._append_log("Bat dau crop video.")
        self._append_log("Command:")
        self._append_log(" ".join(shlex.quote(part) for part in command))

        self.worker_thread = threading.Thread(
            target=self._run_ffmpeg_command,
            args=(command, output_path, self.metadata.duration_seconds),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_ffmpeg_command(
        self,
        command: list[str],
        output_path: Path,
        duration_seconds: Optional[float],
    ) -> None:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            self.message_queue.put(("error", f"Khong the chay ffmpeg: {exc}"))
            return

        self.current_process = process
        stderr_output = ""
        try:
            if process.stdout:
                for raw_line in iter(process.stdout.readline, ""):
                    line = raw_line.strip()
                    if not line or "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    if key == "out_time" and duration_seconds:
                        seconds = parse_ffmpeg_timestamp(value)
                        progress_value = min((seconds / duration_seconds) * 100, 100)
                        self.message_queue.put(("progress", progress_value))
                    elif key == "progress" and value == "end":
                        self.message_queue.put(("progress", 100.0))

            if process.stderr:
                stderr_output = process.stderr.read().strip()
            return_code = process.wait()
        except Exception as exc:  # noqa: BLE001
            process.kill()
            self.message_queue.put(("error", f"Crop bi gian doan: {exc}"))
            return
        finally:
            self.current_process = None

        if stderr_output:
            self.message_queue.put(("log", stderr_output))

        if return_code == 0:
            self.message_queue.put(("done", str(output_path)))
        else:
            error_text = stderr_output or f"ffmpeg ket thuc voi ma loi {return_code}."
            self.message_queue.put(("error", error_text))

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.message_queue.get_nowait()
                if kind == "progress":
                    self._set_progress(float(payload))
                    self._set_status(f"Dang crop video... {float(payload):.1f}%")
                elif kind == "log":
                    self._append_log(str(payload))
                elif kind == "done":
                    self._set_progress(100.0)
                    self._set_status(f"Hoan tat. Da xuat video tai: {payload}")
                    self._append_log(f"Hoan tat: {payload}")
                    self.worker_thread = None
                    self._set_processing_state(False)
                elif kind == "error":
                    self._set_status("Crop that bai.")
                    self._append_log(f"Loi: {payload}")
                    self.worker_thread = None
                    self._set_processing_state(False)
                    self._show_modal("Crop that bai", str(payload))
        except queue.Empty:
            return

    def _set_processing_state(self, is_processing: bool) -> None:
        for tag in self.interactive_tags:
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, enabled=not is_processing)

    def _set_source_info(self, text: str) -> None:
        dpg.set_value(self.tags["source_info"], text)

    def _set_crop_summary(self, text: str) -> None:
        dpg.set_value(self.tags["crop_summary"], text)

    def _set_status(self, text: str) -> None:
        dpg.set_value(self.tags["status_text"], text)

    def _set_preview_hint(self, text: str) -> None:
        dpg.set_value(self.tags["preview_hint"], text)

    def _set_progress(self, progress_percent: float) -> None:
        normalized = max(0.0, min(progress_percent / 100.0, 1.0))
        dpg.set_value(self.tags["progress_bar"], normalized)
        dpg.set_value(self.tags["progress_text"], f"{progress_percent:.1f}%")

    def _set_log(self, text: str) -> None:
        dpg.set_value(self.tags["log_output"], text)

    def _append_log(self, message: str) -> None:
        if not message:
            return

        current = dpg.get_value(self.tags["log_output"])
        next_text = (current + "\n" if current else "") + message.rstrip()
        dpg.set_value(self.tags["log_output"], next_text)

    def _show_modal(self, title: str, message: str) -> None:
        if dpg.does_item_exist(MODAL_TAG):
            dpg.delete_item(MODAL_TAG)

        viewport_width = dpg.get_viewport_client_width() or 1200
        viewport_height = dpg.get_viewport_client_height() or 780
        pos_x = max((viewport_width - 460) // 2, 40)
        pos_y = max((viewport_height - 180) // 2, 40)

        with dpg.window(
            tag=MODAL_TAG,
            label=title,
            modal=True,
            no_resize=True,
            no_move=True,
            no_collapse=True,
            width=460,
            height=180,
            pos=(pos_x, pos_y),
        ):
            dpg.add_text(message, wrap=420)
            dpg.add_spacer(height=12)
            dpg.add_button(label="Dong", width=100, callback=lambda: dpg.delete_item(MODAL_TAG))

    def run(self) -> None:
        dpg.create_viewport(title="Video Crop Studio", width=1220, height=800)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.tags["main_window"], True)

        while dpg.is_dearpygui_running():
            self._poll_messages()
            dpg.render_dearpygui_frame()

        if self.current_process and self.current_process.poll() is None:
            self.current_process.kill()
        self._delete_preview_assets()
        dpg.destroy_context()


def main() -> None:
    app = VideoCropApp()
    app.run()
