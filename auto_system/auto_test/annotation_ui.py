import cv2
import ctypes
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AnnotationTool:
    """
    Lightweight OpenCV annotation tool.

    Keyboard:
    - a/d: switch class
    - n: create a new class during annotation
    - u: undo last bbox
    - s: save current image annotations and continue
    - q/ESC: cancel
    """

    def __init__(
        self,
        image_path: str,
        class_names: List[str],
        image_paths: Optional[List[str]] = None,
        current_image_idx: int = 0,
        initial_annotations: Optional[List[Dict]] = None,
        max_window_size: Tuple[int, int] = (1400, 900),
        initial_window_ratio: float = 0.75,
    ):
        self.image_path = Path(image_path)
        self.class_names = class_names
        self.current_class_idx = 0
        self.annotations: List[Dict] = []
        self.max_window_size = max_window_size

        self.image = cv2.imread(str(self.image_path))
        if self.image is None:
            raise ValueError(f"Failed to load image: {self.image_path}")

        self.image_h, self.image_w = self.image.shape[:2]
        max_w, max_h = self.max_window_size
        fit_scale = min(max_w / self.image_w, max_h / self.image_h, 1.0)
        fit_w = max(1, int(self.image_w * fit_scale))
        fit_h = max(1, int(self.image_h * fit_scale))
        ratio = max(0.3, min(float(initial_window_ratio), 1.0))
        # Shrink only for large initial viewports so startup does not occupy most of desktop.
        if fit_w >= 1200 or fit_h >= 800:
            fit_w = max(640, int(fit_w * ratio))
            fit_h = max(360, int(fit_h * ratio))
        self.display_scale = min(fit_w / self.image_w, fit_h / self.image_h)
        self.display_w = fit_w
        self.display_h = fit_h
        self.viewport_w = self.display_w
        self.viewport_h = self.display_h

        self.display_image = self.image.copy()
        self.window_name = "YOLO Annotation Tool - Image"
        self.class_window_name = "YOLO Annotation Tool - Classes"
        self.class_panel_width = 360
        self.class_panel_h = self._calc_class_panel_height()
        self.class_row_h = 34
        self.class_scroll_offset = 0
        self.image_scroll_offset = 0
        self.panel_image = None
        self.class_list_rect: Tuple[int, int, int, int] = (
            12,
            140,
            self.class_panel_width - 12,
            self.class_panel_h - 92,
        )
        self.image_list_rect: Tuple[int, int, int, int] = (
            12,
            140,
            self.class_panel_width - 12,
            self.class_panel_h - 92,
        )
        self.image_names = [Path(p).name for p in (image_paths or [str(self.image_path)])]
        self.current_image_idx = max(0, min(current_image_idx, len(self.image_names) - 1))
        self.pending_jump_image_idx: Optional[int] = None
        self.auto_save_and_jump = False
        self.finish_session = False
        if initial_annotations:
            # Load existing labels when revisiting an image.
            self.annotations = [
                {
                    "bbox": list(ann.get("bbox", [])),
                    "class_idx": int(ann.get("class_idx", 0)),
                    "class_name": str(ann.get("class_name", "")),
                }
                for ann in initial_annotations
                if isinstance(ann, dict) and "bbox" in ann
            ]

        self.drawing = False
        self.start_point: Optional[Tuple[int, int]] = None
        self.current_bbox: Optional[List[int]] = None
        self.adding_new_class = False
        self.new_class_buffer = ""
        self._arrow_cursor = None

    def _calc_class_panel_height(self) -> int:
        try:
            screen_h = int(ctypes.windll.user32.GetSystemMetrics(1))
            return max(360, int(screen_h * 0.8))
        except Exception:
            return max(360, self.display_h)

    def _class_list_rect(self) -> Tuple[int, int, int, int]:
        return self.class_list_rect

    def _image_list_rect(self) -> Tuple[int, int, int, int]:
        return self.image_list_rect

    def _visible_class_rows(self) -> int:
        _, y1, _, y2 = self._class_list_rect()
        h = max(0, y2 - y1)
        return max(1, h // self.class_row_h)

    def _visible_image_rows(self) -> int:
        _, y1, _, y2 = self._image_list_rect()
        h = max(0, y2 - y1)
        return max(1, h // self.class_row_h)

    def _ensure_scroll_bounds(self) -> None:
        max_offset = max(0, len(self.class_names) - self._visible_class_rows())
        self.class_scroll_offset = max(0, min(self.class_scroll_offset, max_offset))
        max_img_offset = max(0, len(self.image_names) - self._visible_image_rows())
        self.image_scroll_offset = max(0, min(self.image_scroll_offset, max_img_offset))

    def _ensure_selected_visible(self) -> None:
        visible = self._visible_class_rows()
        if self.current_class_idx < self.class_scroll_offset:
            self.class_scroll_offset = self.current_class_idx
        elif self.current_class_idx >= self.class_scroll_offset + visible:
            self.class_scroll_offset = self.current_class_idx - visible + 1
        self._ensure_scroll_bounds()

    def _scroll_classes(self, delta: int) -> None:
        self.class_scroll_offset += delta
        self._ensure_scroll_bounds()

    def _scroll_images(self, delta: int) -> None:
        self.image_scroll_offset += delta
        self._ensure_scroll_bounds()

    @staticmethod
    def _mouse_wheel_delta(flags: int) -> int:
        if hasattr(cv2, "getMouseWheelDelta"):
            return int(cv2.getMouseWheelDelta(flags))
        # Fallback for older OpenCV.
        return 1 if flags > 0 else -1

    def _to_original(self, x: int, y: int) -> Tuple[int, int]:
        sx = self.image_w / max(1, self.viewport_w)
        sy = self.image_h / max(1, self.viewport_h)
        ox = int(round(x * sx))
        oy = int(round(y * sy))
        ox = max(0, min(self.image_w - 1, ox))
        oy = max(0, min(self.image_h - 1, oy))
        return ox, oy

    def _to_display(self, x: int, y: int) -> Tuple[int, int]:
        sx = self.viewport_w / max(1, self.image_w)
        sy = self.viewport_h / max(1, self.image_h)
        dx = int(round(x * sx))
        dy = int(round(y * sy))
        dx = max(0, min(self.viewport_w - 1, dx))
        dy = max(0, min(self.viewport_h - 1, dy))
        return dx, dy

    def _update_viewport_size(self) -> None:
        # Read current displayed image area size to keep mouse->image mapping correct
        # when user resizes the image window.
        try:
            _, _, w, h = cv2.getWindowImageRect(self.window_name)
            if w > 0 and h > 0:
                self.viewport_w = int(w)
                self.viewport_h = int(h)
        except Exception:
            # Fallback: keep initial viewport.
            self.viewport_w = self.display_w
            self.viewport_h = self.display_h

    def _mouse_callback(self, event, x, y, flags, param):
        if self.adding_new_class:
            return

        # Ignore drawing events outside image viewport.
        if x < 0 or y < 0 or x >= self.viewport_w or y >= self.viewport_h:
            return

        ox, oy = self._to_original(x, y)

        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (ox, oy)
            self.current_bbox = [ox, oy, ox, oy]
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing and self.current_bbox is not None:
            self.current_bbox[2], self.current_bbox[3] = ox, oy
        elif event == cv2.EVENT_LBUTTONUP and self.drawing:
            self.drawing = False
            if self.start_point is None:
                return
            x1, y1 = self.start_point
            x2, y2 = ox, oy
            x_min, x_max = sorted([x1, x2])
            y_min, y_max = sorted([y1, y2])
            if (x_max - x_min) > 5 and (y_max - y_min) > 5:
                self.annotations.append(
                    {
                        "bbox": [x_min, y_min, x_max, y_max],
                        "class_idx": self.current_class_idx,
                        "class_name": self.class_names[self.current_class_idx],
                    }
                )
            self.current_bbox = None

    def _class_mouse_callback(self, event, x, y, flags, param):
        self._set_arrow_cursor()
        if self.adding_new_class:
            return
        if event == cv2.EVENT_MOUSEWHEEL:
            delta = self._mouse_wheel_delta(flags)
            cx1, cy1, cx2, cy2 = self._class_list_rect()
            ix1, iy1, ix2, iy2 = self._image_list_rect()
            if cx1 <= x <= cx2 and cy1 <= y <= cy2:
                if delta > 0:
                    self._scroll_classes(-1)
                elif delta < 0:
                    self._scroll_classes(1)
            elif ix1 <= x <= ix2 and iy1 <= y <= iy2:
                if delta > 0:
                    self._scroll_images(-1)
                elif delta < 0:
                    self._scroll_images(1)
            return
        if event in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_LBUTTONDBLCLK):
            x1, y1, x2, y2 = self._class_list_rect()
            if x1 <= x <= x2 and y1 <= y <= y2:
                row = (y - y1) // self.class_row_h
                idx = self.class_scroll_offset + row
                if 0 <= idx < len(self.class_names):
                    self.current_class_idx = idx
                    self._ensure_selected_visible()
                return

            x1, y1, x2, y2 = self._image_list_rect()
            if x1 <= x <= x2 and y1 <= y <= y2:
                row = (y - y1) // self.class_row_h
                idx = self.image_scroll_offset + row
                if 0 <= idx < len(self.image_names):
                    self.pending_jump_image_idx = idx
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.auto_save_and_jump = False
                    if event == cv2.EVENT_LBUTTONDBLCLK and idx != self.current_image_idx:
                        self.auto_save_and_jump = True

    def _set_arrow_cursor(self) -> None:
        # Windows-only best effort: force arrow cursor in class list window.
        try:
            if self._arrow_cursor is None:
                self._arrow_cursor = ctypes.windll.user32.LoadCursorW(0, 32512)  # IDC_ARROW
            ctypes.windll.user32.SetCursor(self._arrow_cursor)
        except Exception:
            pass

    def _truncate_text(self, text: str, max_width: int, font_scale: float, thickness: int) -> str:
        if not text:
            return text
        out = text
        while out:
            w, _ = cv2.getTextSize(out, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
            if w <= max_width:
                return out
            if len(out) <= 1:
                break
            out = out[:-1]
            if len(out) > 1:
                out = out[:-1] + "..."
        return text[:1]

    def _draw(self):
        canvas = self.image.copy()

        for ann in self.annotations:
            x1, y1, x2, y2 = ann["bbox"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                canvas,
                ann["class_name"],
                (x1, max(20, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        if self.current_bbox is not None:
            x1, y1, x2, y2 = self.current_bbox
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 200, 255), 2)

        if self.display_scale != 1.0:
            self.display_image = cv2.resize(
                canvas, (self.viewport_w, self.viewport_h), interpolation=cv2.INTER_AREA
            )
        else:
            self.display_image = canvas

        self._ensure_scroll_bounds()
        self._ensure_selected_visible()

        panel = np.full((self.class_panel_h, self.class_panel_width, 3), 245, dtype=np.uint8)
        cv2.rectangle(
            panel,
            (0, 0),
            (self.class_panel_width - 1, self.class_panel_h - 1),
            (60, 60, 60),
            1,
        )
        current_text = f"Current: {self.class_names[self.current_class_idx]}"
        current_text = self._truncate_text(current_text, self.class_panel_width - 24, 0.62, 2)
        cv2.putText(panel, current_text, (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (30, 100, 30), 2)

        # Fixed section layout (avoid overlap/cut):
        # header area -> optional input area -> list area -> footer help area
        header_h = 80
        input_h = 58 if self.adding_new_class else 0
        footer_h = 150
        outer_pad = 10
        inner_gap = 8
        list_top = header_h + input_h + inner_gap
        list_bottom = self.class_panel_h - footer_h - inner_gap
        if list_bottom - list_top < self.class_row_h:
            list_bottom = list_top + self.class_row_h
        mid_gap = 18
        split_mid = (list_top + list_bottom) // 2
        class_bottom = split_mid - mid_gap
        image_top = split_mid + mid_gap
        if class_bottom - list_top < self.class_row_h:
            class_bottom = list_top + self.class_row_h
        if list_bottom - image_top < self.class_row_h:
            image_top = list_bottom - self.class_row_h
        self.class_list_rect = (12, list_top, self.class_panel_width - 12, class_bottom)
        self.image_list_rect = (12, image_top, self.class_panel_width - 12, list_bottom)

        list_x1, list_y1, list_x2, list_y2 = self._class_list_rect()
        cv2.putText(panel, "Classes", (12, list_y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (45, 45, 45), 1)
        cv2.rectangle(panel, (list_x1, list_y1), (list_x2, list_y2), (120, 120, 120), 1)

        visible_rows = self._visible_class_rows()
        start = self.class_scroll_offset
        end = min(len(self.class_names), start + visible_rows)
        y = list_y1
        for idx in range(start, end):
            is_selected = idx == self.current_class_idx
            bg = (220, 245, 220) if is_selected else (245, 245, 245)
            fg = (10, 90, 10) if is_selected else (40, 40, 40)
            cv2.rectangle(panel, (list_x1 + 1, y + 1), (list_x2 - 1, y + self.class_row_h - 1), bg, -1)
            cv2.putText(
                panel,
                self._truncate_text(f"{idx + 1}. {self.class_names[idx]}", (list_x2 - list_x1) - 20, 0.72, 2),
                (list_x1 + 10, y + 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72,
                fg,
                2,
            )
            y += self.class_row_h

        if len(self.class_names) > visible_rows:
            cv2.putText(
                panel,
                f"Showing {start + 1}-{end} / {len(self.class_names)}",
                (list_x1 + 6, list_y2 - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                (80, 80, 80),
                1,
            )

        # Image list
        ix1, iy1, ix2, iy2 = self._image_list_rect()
        cv2.putText(panel, "Images", (12, iy1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (45, 45, 45), 1)
        cv2.rectangle(panel, (ix1, iy1), (ix2, iy2), (120, 120, 120), 1)

        visible_img_rows = self._visible_image_rows()
        img_start = self.image_scroll_offset
        img_end = min(len(self.image_names), img_start + visible_img_rows)
        y = iy1
        for idx in range(img_start, img_end):
            is_current = idx == self.current_image_idx
            is_target = self.pending_jump_image_idx is not None and idx == self.pending_jump_image_idx
            if is_target:
                bg = (255, 235, 210)
                fg = (120, 70, 20)
            elif is_current:
                bg = (220, 235, 255)
                fg = (20, 70, 120)
            else:
                bg = (245, 245, 245)
                fg = (40, 40, 40)
            cv2.rectangle(panel, (ix1 + 1, y + 1), (ix2 - 1, y + self.class_row_h - 1), bg, -1)
            label = self._truncate_text(f"{idx + 1}. {self.image_names[idx]}", (ix2 - ix1) - 20, 0.58, 1)
            cv2.putText(panel, label, (ix1 + 8, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.58, fg, 1)
            y += self.class_row_h

        # Footer help area.
        help_top = self.class_panel_h - footer_h
        help_bottom = self.class_panel_h - outer_pad
        cv2.rectangle(panel, (outer_pad, help_top), (self.class_panel_width - outer_pad, help_bottom), (210, 210, 210), 1)
        cv2.putText(panel, "Hotkeys:", (16, help_top + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
        cv2.putText(panel, "a / d: switch class", (16, help_top + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
        cv2.putText(panel, "s: save and finish", (16, help_top + 62), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
        cv2.putText(panel, "n: new class", (16, help_top + 82), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
        cv2.putText(panel, "q / Esc: quit", (16, help_top + 102), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
        cv2.putText(panel, "double-click image: save + switch", (16, help_top + 122), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (50, 50, 50), 1)

        if self.adding_new_class:
            cv2.rectangle(panel, (10, 118), (self.class_panel_width - 10, 172), (230, 245, 255), -1)
            cv2.rectangle(panel, (10, 118), (self.class_panel_width - 10, 172), (120, 160, 190), 1)
            cv2.putText(panel, f"new class: {self.new_class_buffer}_", (16, 143), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (30, 90, 120), 1)
            cv2.putText(panel, "Enter confirm | Backspace delete | Esc cancel", (16, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (30, 90, 120), 1)

        self.panel_image = panel

    def run(self) -> Optional[List[Dict]]:
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.namedWindow(self.class_window_name, cv2.WINDOW_AUTOSIZE)
        cv2.resizeWindow(self.window_name, self.display_w, self.display_h)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        cv2.setMouseCallback(self.class_window_name, self._class_mouse_callback)

        while True:
            self._update_viewport_size()
            self._draw()
            cv2.imshow(self.window_name, self.display_image)
            cv2.imshow(self.class_window_name, self.panel_image)

            if self.auto_save_and_jump:
                self.auto_save_and_jump = False
                cv2.destroyAllWindows()
                return self.annotations

            key = cv2.waitKey(1) & 0xFF

            if self.adding_new_class:
                if key in (13, 10):  # Enter
                    class_name = self.new_class_buffer.strip()
                    if class_name:
                        if class_name not in self.class_names:
                            self.class_names.append(class_name)
                        self.current_class_idx = self.class_names.index(class_name)
                    self.adding_new_class = False
                    self.new_class_buffer = ""
                elif key == 8:  # Backspace
                    self.new_class_buffer = self.new_class_buffer[:-1]
                elif key == 27:  # ESC
                    self.adding_new_class = False
                    self.new_class_buffer = ""
                elif 32 <= key <= 126:
                    self.new_class_buffer += chr(key)
                continue

            if key == ord("a"):
                self.current_class_idx = (self.current_class_idx - 1) % len(self.class_names)
                self._ensure_selected_visible()
            elif key == ord("d"):
                self.current_class_idx = (self.current_class_idx + 1) % len(self.class_names)
                self._ensure_selected_visible()
            elif key == ord("n"):
                self.adding_new_class = True
                self.new_class_buffer = ""
            elif key == ord("u") and self.annotations:
                self.annotations.pop()
            elif key == ord("s"):
                self.finish_session = True
                cv2.destroyAllWindows()
                return self.annotations
            elif key == ord("q") or key == 27:
                cv2.destroyAllWindows()
                return None
