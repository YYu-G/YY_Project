import cv2
import ctypes
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None


class AnnotationTool:
    """
    Lightweight OpenCV annotation tool.

    Keyboard:
    - a/d: switch class
    - n: create a new class during annotation
    - u: undo last bbox
    - s: save current image annotations and continue
    - Save Dataset button: save all annotated images and build dataset
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
        self.class_x_scroll_offset = 0
        self.image_x_scroll_offset = 0
        self.scrollbar_size = 10
        self._scrollbar_rects: Dict[Tuple[str, str], Tuple[int, int, int, int]] = {}
        self._scrollbar_drag = None
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
        self.save_dataset_requested = False
        self.finish_session = False
        self.save_dataset_button_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self._font_cache: Dict[Tuple[int, int], Any] = {}
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
            return max(620, min(760, int(screen_h * 0.70)))
        except Exception:
            return max(620, min(760, self.display_h))

    def _class_list_rect(self) -> Tuple[int, int, int, int]:
        return self.class_list_rect

    def _image_list_rect(self) -> Tuple[int, int, int, int]:
        return self.image_list_rect

    @staticmethod
    def _point_in_rect(x: int, y: int, rect: Tuple[int, int, int, int]) -> bool:
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _has_non_ascii(text: str) -> bool:
        return any(ord(ch) > 127 for ch in text)

    def _font_size(self, font_scale: float) -> int:
        return max(10, int(round(font_scale * 30)))

    def _get_font(self, font_scale: float, thickness: int):
        font_size = self._font_size(font_scale)
        key = (font_size, thickness)
        if key in self._font_cache:
            return self._font_cache[key]
        if ImageFont is None:
            return None

        font_candidates = [
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/simhei.ttf"),
            Path("C:/Windows/Fonts/simsun.ttc"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
        font = None
        for font_path in font_candidates:
            if font_path.exists():
                try:
                    font = ImageFont.truetype(str(font_path), font_size)
                    break
                except Exception:
                    pass
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
        self._font_cache[key] = font
        return font

    def _text_width(self, text: str, font_scale: float, thickness: int) -> int:
        if self._has_non_ascii(text) and ImageDraw is not None:
            font = self._get_font(font_scale, thickness)
            if font is not None:
                bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
                return max(0, bbox[2] - bbox[0])
        return cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0][0]

    def _put_text(
        self,
        image: np.ndarray,
        text: str,
        org: Tuple[int, int],
        font_scale: float,
        color: Tuple[int, int, int],
        thickness: int = 1,
    ) -> None:
        if not self._has_non_ascii(text) or Image is None or ImageDraw is None:
            cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            return

        font = self._get_font(font_scale, thickness)
        if font is None:
            cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            return

        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        x, baseline_y = org
        y = baseline_y - self._font_size(font_scale)
        rgb = (int(color[2]), int(color[1]), int(color[0]))
        draw.text((x, y), text, font=font, fill=rgb)
        image[:, :] = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR)

    def _class_label(self, idx: int) -> str:
        return f"{idx + 1}. {self.class_names[idx]}"

    def _image_label(self, idx: int) -> str:
        return f"{idx + 1}. {self.image_names[idx]}"

    def _list_count(self, kind: str) -> int:
        return len(self.class_names) if kind == "class" else len(self.image_names)

    def _list_text_style(self, kind: str) -> Tuple[float, int]:
        return (0.72, 2) if kind == "class" else (0.58, 1)

    def _list_x_offset(self, kind: str) -> int:
        return self.class_x_scroll_offset if kind == "class" else self.image_x_scroll_offset

    def _set_list_x_offset(self, kind: str, value: int) -> None:
        if kind == "class":
            self.class_x_scroll_offset = value
        else:
            self.image_x_scroll_offset = value

    def _list_max_text_width(self, kind: str) -> int:
        font_scale, thickness = self._list_text_style(kind)
        if kind == "class":
            if not self.class_names:
                return self._text_width("暂无类别，按 n 新建。", 0.55, 1)
            return max((self._text_width(self._class_label(i), font_scale, thickness) for i in range(len(self.class_names))), default=0)
        return max((self._text_width(self._image_label(i), font_scale, thickness) for i in range(len(self.image_names))), default=0)

    def _list_metrics(self, kind: str) -> Dict[str, Any]:
        x1, y1, x2, y2 = self._class_list_rect() if kind == "class" else self._image_list_rect()
        inside_x1 = x1 + 1
        inside_y1 = y1 + 1
        inside_w = max(1, x2 - x1 - 2)
        inside_h = max(1, y2 - y1 - 2)
        count = self._list_count(kind)
        content_w = self._list_max_text_width(kind) + 16
        bar = self.scrollbar_size

        has_v = False
        has_h = False
        viewport_w = inside_w
        viewport_h = inside_h
        visible_rows = max(1, viewport_h // self.class_row_h)

        for _ in range(3):
            viewport_w = max(1, inside_w - (bar if has_v else 0))
            viewport_h = max(1, inside_h - (bar if has_h else 0))
            visible_rows = max(1, viewport_h // self.class_row_h)
            next_has_v = count > visible_rows
            next_has_h = content_w > viewport_w
            if next_has_v == has_v and next_has_h == has_h:
                break
            has_v = next_has_v
            has_h = next_has_h

        viewport_w = max(1, inside_w - (bar if has_v else 0))
        viewport_h = max(1, inside_h - (bar if has_h else 0))
        visible_rows = max(1, viewport_h // self.class_row_h)
        max_y_offset = max(0, count - visible_rows)
        max_x_offset = max(0, content_w - viewport_w)
        viewport_rect = (inside_x1, inside_y1, inside_x1 + viewport_w, inside_y1 + viewport_h)
        v_track = (
            inside_x1 + viewport_w,
            inside_y1,
            inside_x1 + viewport_w + bar - 1,
            inside_y1 + viewport_h - 1,
        ) if has_v else (0, 0, 0, 0)
        h_track = (
            inside_x1,
            inside_y1 + viewport_h,
            inside_x1 + viewport_w - 1,
            inside_y1 + viewport_h + bar - 1,
        ) if has_h else (0, 0, 0, 0)

        def thumb(track: Tuple[int, int, int, int], axis: str) -> Tuple[int, int, int, int]:
            tx1, ty1, tx2, ty2 = track
            if axis == "v":
                track_len = max(1, ty2 - ty1 + 1)
                max_offset = max_y_offset
                ratio = visible_rows / max(1, count)
                thumb_len = max(18, min(track_len, int(track_len * ratio)))
                free = max(0, track_len - thumb_len)
                pos = int(round(free * (self.class_scroll_offset if kind == "class" else self.image_scroll_offset) / max(1, max_offset)))
                return (tx1, ty1 + pos, tx2, ty1 + pos + thumb_len - 1)
            track_len = max(1, tx2 - tx1 + 1)
            max_offset = max_x_offset
            ratio = viewport_w / max(1, content_w)
            thumb_len = max(18, min(track_len, int(track_len * ratio)))
            free = max(0, track_len - thumb_len)
            pos = int(round(free * self._list_x_offset(kind) / max(1, max_offset)))
            return (tx1 + pos, ty1, tx1 + pos + thumb_len - 1, ty2)

        v_thumb = thumb(v_track, "v") if has_v else (0, 0, 0, 0)
        h_thumb = thumb(h_track, "h") if has_h else (0, 0, 0, 0)

        return {
            "rect": (x1, y1, x2, y2),
            "viewport_rect": viewport_rect,
            "count": count,
            "content_w": content_w,
            "visible_rows": visible_rows,
            "has_v": has_v,
            "has_h": has_h,
            "max_y_offset": max_y_offset,
            "max_x_offset": max_x_offset,
            "v_track": v_track,
            "v_thumb": v_thumb,
            "h_track": h_track,
            "h_thumb": h_thumb,
        }

    def _visible_class_rows(self) -> int:
        return int(self._list_metrics("class")["visible_rows"])

    def _visible_image_rows(self) -> int:
        return int(self._list_metrics("image")["visible_rows"])

    def _ensure_scroll_bounds(self) -> None:
        class_metrics = self._list_metrics("class")
        self.class_scroll_offset = max(0, min(self.class_scroll_offset, int(class_metrics["max_y_offset"])))
        self.class_x_scroll_offset = max(0, min(self.class_x_scroll_offset, int(class_metrics["max_x_offset"])))
        image_metrics = self._list_metrics("image")
        self.image_scroll_offset = max(0, min(self.image_scroll_offset, int(image_metrics["max_y_offset"])))
        self.image_x_scroll_offset = max(0, min(self.image_x_scroll_offset, int(image_metrics["max_x_offset"])))

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

    def _scroll_horizontal(self, kind: str, delta: int) -> None:
        self._set_list_x_offset(kind, self._list_x_offset(kind) + delta)
        self._ensure_scroll_bounds()

    @staticmethod
    def _mouse_wheel_delta(flags: int) -> int:
        if hasattr(cv2, "getMouseWheelDelta"):
            return int(cv2.getMouseWheelDelta(flags))
        # Fallback for older OpenCV.
        return 1 if flags > 0 else -1

    def _register_scrollbars(self, kind: str, metrics: Dict[str, Any]) -> None:
        for axis in ("v", "h"):
            if metrics.get(f"has_{axis}"):
                self._scrollbar_rects[(kind, f"{axis}_track")] = metrics[f"{axis}_track"]
                self._scrollbar_rects[(kind, f"{axis}_thumb")] = metrics[f"{axis}_thumb"]

    def _find_scrollbar_hit(self, x: int, y: int) -> Optional[Tuple[str, str, str]]:
        for (kind, part), rect in self._scrollbar_rects.items():
            if part.endswith("_thumb") and self._point_in_rect(x, y, rect):
                return kind, part[0], "thumb"
        for (kind, part), rect in self._scrollbar_rects.items():
            if part.endswith("_track") and self._point_in_rect(x, y, rect):
                return kind, part[0], "track"
        return None

    def _set_vertical_scroll_offset(self, kind: str, value: int) -> None:
        if kind == "class":
            self.class_scroll_offset = value
        else:
            self.image_scroll_offset = value
        self._ensure_scroll_bounds()

    def _page_scroll_from_track(self, kind: str, axis: str, x: int, y: int) -> None:
        metrics = self._list_metrics(kind)
        thumb = metrics[f"{axis}_thumb"]
        if axis == "v":
            step = int(metrics["visible_rows"])
            current = self.class_scroll_offset if kind == "class" else self.image_scroll_offset
            _, thumb_y1, _, thumb_y2 = thumb
            if y < thumb_y1:
                self._set_vertical_scroll_offset(kind, current - step)
            elif y > thumb_y2:
                self._set_vertical_scroll_offset(kind, current + step)
            return

        step = max(24, metrics["viewport_rect"][2] - metrics["viewport_rect"][0])
        current = self._list_x_offset(kind)
        thumb_x1, _, thumb_x2, _ = thumb
        if x < thumb_x1:
            self._scroll_horizontal(kind, -step)
        elif x > thumb_x2:
            self._scroll_horizontal(kind, step)

    def _start_scrollbar_drag(self, kind: str, axis: str, x: int, y: int) -> None:
        self._scrollbar_drag = {
            "kind": kind,
            "axis": axis,
            "start_coord": y if axis == "v" else x,
            "start_offset": self.class_scroll_offset if kind == "class" and axis == "v"
            else self.image_scroll_offset if axis == "v"
            else self._list_x_offset(kind),
        }

    def _update_scrollbar_drag(self, x: int, y: int) -> None:
        if not self._scrollbar_drag:
            return
        kind = str(self._scrollbar_drag["kind"])
        axis = str(self._scrollbar_drag["axis"])
        start_coord = int(self._scrollbar_drag["start_coord"])
        start_offset = int(self._scrollbar_drag["start_offset"])
        metrics = self._list_metrics(kind)

        if axis == "v":
            track = metrics["v_track"]
            thumb = metrics["v_thumb"]
            track_len = max(1, track[3] - track[1] + 1)
            thumb_len = max(1, thumb[3] - thumb[1] + 1)
            free = max(1, track_len - thumb_len)
            max_offset = int(metrics["max_y_offset"])
            new_offset = start_offset + int(round((y - start_coord) * max_offset / free))
            self._set_vertical_scroll_offset(kind, new_offset)
            return

        track = metrics["h_track"]
        thumb = metrics["h_thumb"]
        track_len = max(1, track[2] - track[0] + 1)
        thumb_len = max(1, thumb[2] - thumb[0] + 1)
        free = max(1, track_len - thumb_len)
        max_offset = int(metrics["max_x_offset"])
        new_offset = start_offset + int(round((x - start_coord) * max_offset / free))
        self._scroll_horizontal(kind, new_offset - self._list_x_offset(kind))

    def _handle_scrollbar_mouse(self, event: int, x: int, y: int) -> bool:
        if self._scrollbar_drag:
            if event == cv2.EVENT_MOUSEMOVE:
                self._update_scrollbar_drag(x, y)
                return True
            if event == cv2.EVENT_LBUTTONUP:
                self._update_scrollbar_drag(x, y)
                self._scrollbar_drag = None
                return True

        if event != cv2.EVENT_LBUTTONDOWN:
            return False

        hit = self._find_scrollbar_hit(x, y)
        if not hit:
            return False

        kind, axis, target = hit
        if target == "thumb":
            self._start_scrollbar_drag(kind, axis, x, y)
        else:
            self._page_scroll_from_track(kind, axis, x, y)
        return True

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
        if not self.class_names:
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
        if self._handle_scrollbar_mouse(event, x, y):
            return
        if self.adding_new_class:
            return
        if event == cv2.EVENT_MOUSEWHEEL:
            delta = self._mouse_wheel_delta(flags)
            shift_pressed = bool(flags & getattr(cv2, "EVENT_FLAG_SHIFTKEY", 16))
            cx1, cy1, cx2, cy2 = self._class_list_rect()
            ix1, iy1, ix2, iy2 = self._image_list_rect()
            if cx1 <= x <= cx2 and cy1 <= y <= cy2:
                if shift_pressed and int(self._list_metrics("class")["max_x_offset"]) > 0:
                    self._scroll_horizontal("class", -40 if delta > 0 else 40)
                elif delta > 0:
                    self._scroll_classes(-1)
                elif delta < 0:
                    self._scroll_classes(1)
            elif ix1 <= x <= ix2 and iy1 <= y <= iy2:
                if shift_pressed and int(self._list_metrics("image")["max_x_offset"]) > 0:
                    self._scroll_horizontal("image", -40 if delta > 0 else 40)
                elif delta > 0:
                    self._scroll_images(-1)
                elif delta < 0:
                    self._scroll_images(1)
            return
        if event in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_LBUTTONDBLCLK):
            sx1, sy1, sx2, sy2 = self.save_dataset_button_rect
            if sx1 <= x <= sx2 and sy1 <= y <= sy2:
                self.save_dataset_requested = True
                self.finish_session = True
                return

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

        max_width = max(0, int(max_width))

        def text_width(value: str) -> int:
            return self._text_width(value, font_scale, thickness)

        if text_width(text) <= max_width:
            return text

        ellipsis = "..."
        if text_width(ellipsis) > max_width:
            return text[:1] if text_width(text[:1]) <= max_width else ""

        low = 0
        high = len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if text_width(text[:mid] + ellipsis) <= max_width:
                low = mid
            else:
                high = mid - 1

        return text[:low] + ellipsis if low > 0 else ellipsis

    def _draw_scrollbars(self, panel: np.ndarray, metrics: Dict[str, Any]) -> None:
        track_color = (226, 226, 226)
        thumb_color = (150, 150, 150)
        thumb_border = (110, 110, 110)

        if metrics["has_v"]:
            cv2.rectangle(panel, metrics["v_track"][:2], metrics["v_track"][2:], track_color, -1)
            cv2.rectangle(panel, metrics["v_track"][:2], metrics["v_track"][2:], (190, 190, 190), 1)
            cv2.rectangle(panel, metrics["v_thumb"][:2], metrics["v_thumb"][2:], thumb_color, -1)
            cv2.rectangle(panel, metrics["v_thumb"][:2], metrics["v_thumb"][2:], thumb_border, 1)

        if metrics["has_h"]:
            cv2.rectangle(panel, metrics["h_track"][:2], metrics["h_track"][2:], track_color, -1)
            cv2.rectangle(panel, metrics["h_track"][:2], metrics["h_track"][2:], (190, 190, 190), 1)
            cv2.rectangle(panel, metrics["h_thumb"][:2], metrics["h_thumb"][2:], thumb_color, -1)
            cv2.rectangle(panel, metrics["h_thumb"][:2], metrics["h_thumb"][2:], thumb_border, 1)

        if metrics["has_v"] and metrics["has_h"]:
            vx1, _, vx2, _ = metrics["v_track"]
            _, hy1, _, hy2 = metrics["h_track"]
            cv2.rectangle(panel, (vx1, hy1), (vx2, hy2), (215, 215, 215), -1)
            cv2.rectangle(panel, (vx1, hy1), (vx2, hy2), (190, 190, 190), 1)

    def _draw_list_contents(self, panel: np.ndarray, kind: str, metrics: Dict[str, Any]) -> None:
        vx1, vy1, vx2, vy2 = metrics["viewport_rect"]
        viewport_w = max(1, vx2 - vx1)
        viewport_h = max(1, vy2 - vy1)
        view = np.full((viewport_h, viewport_w, 3), 245, dtype=np.uint8)
        x_offset = self._list_x_offset(kind)

        if kind == "class":
            start = self.class_scroll_offset
            end = min(len(self.class_names), start + int(metrics["visible_rows"]))
            if not self.class_names:
                self._put_text(
                    view,
                    "暂无类别，按 n 新建。",
                    (8 - x_offset, 24),
                    0.55,
                    (80, 80, 80),
                    1,
                )
            else:
                y = 0
                for idx in range(start, end):
                    is_selected = idx == self.current_class_idx
                    bg = (220, 245, 220) if is_selected else (245, 245, 245)
                    fg = (10, 90, 10) if is_selected else (40, 40, 40)
                    cv2.rectangle(view, (0, y), (viewport_w - 1, min(viewport_h - 1, y + self.class_row_h - 1)), bg, -1)
                    self._put_text(
                        view,
                        self._class_label(idx),
                        (8 - x_offset, y + 24),
                        0.72,
                        fg,
                        2,
                    )
                    y += self.class_row_h
        else:
            start = self.image_scroll_offset
            end = min(len(self.image_names), start + int(metrics["visible_rows"]))
            y = 0
            for idx in range(start, end):
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
                cv2.rectangle(view, (0, y), (viewport_w - 1, min(viewport_h - 1, y + self.class_row_h - 1)), bg, -1)
                self._put_text(
                    view,
                    self._image_label(idx),
                    (8 - x_offset, y + 22),
                    0.58,
                    fg,
                    1,
                )
                y += self.class_row_h

        panel[vy1:vy2, vx1:vx2] = view
        self._draw_scrollbars(panel, metrics)

    def _draw(self):
        canvas = self.image.copy()

        for ann in self.annotations:
            x1, y1, x2, y2 = ann["bbox"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
            self._put_text(
                canvas,
                ann["class_name"],
                (x1, max(20, y1 - 5)),
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
        current_class = self.class_names[self.current_class_idx] if self.class_names else "无"
        current_text = f"当前：{current_class}"
        current_text = self._truncate_text(current_text, self.class_panel_width - 24, 0.62, 2)
        self._put_text(panel, current_text, (12, 42), 0.62, (30, 100, 30), 2)

        # Fixed section layout (avoid overlap/cut):
        # header area -> optional input area -> list area -> footer help area
        header_h = 54
        input_h = 58
        footer_h = 204
        outer_pad = 10
        inner_gap = 8
        list_top = header_h + input_h + inner_gap
        list_bottom = self.class_panel_h - footer_h - inner_gap
        section_gap = 22
        min_list_h = self.class_row_h * 4 + section_gap
        if list_bottom - list_top < min_list_h:
            list_bottom = list_top + min_list_h

        list_h = list_bottom - list_top
        shared_h = max(self.class_row_h * 2, (list_h - section_gap) // 2)
        class_h = shared_h
        image_h = shared_h

        class_bottom = list_top + class_h
        image_top = class_bottom + section_gap
        self.class_list_rect = (12, list_top, self.class_panel_width - 12, class_bottom)
        self.image_list_rect = (12, image_top, self.class_panel_width - 12, image_top + image_h)
        self._ensure_scroll_bounds()
        self._ensure_selected_visible()

        self._scrollbar_rects = {}
        class_metrics = self._list_metrics("class")
        image_metrics = self._list_metrics("image")
        self._register_scrollbars("class", class_metrics)
        self._register_scrollbars("image", image_metrics)

        # Class list
        list_x1, list_y1, list_x2, list_y2 = self._class_list_rect()
        self._put_text(panel, "类别列表", (12, list_y1 - 8), 0.55, (45, 45, 45), 1)
        cv2.rectangle(panel, (list_x1, list_y1), (list_x2, list_y2), (120, 120, 120), 1)
        visible_rows = int(class_metrics["visible_rows"])
        start = self.class_scroll_offset
        end = min(len(self.class_names), start + visible_rows)
        if int(class_metrics["max_y_offset"]) > 0:
            status_text = f"{start + 1}-{end} / {len(self.class_names)}"
            status_w = self._text_width(status_text, 0.46, 1)
            self._put_text(
                panel,
                status_text,
                (list_x2 - status_w - 6, list_y1 - 8),
                0.46,
                (80, 80, 80),
                1,
            )
        self._draw_list_contents(panel, "class", class_metrics)

        # Image list
        ix1, iy1, ix2, iy2 = self._image_list_rect()
        self._put_text(panel, "图片列表", (12, iy1 - 8), 0.55, (45, 45, 45), 1)
        cv2.rectangle(panel, (ix1, iy1), (ix2, iy2), (120, 120, 120), 1)

        visible_img_rows = int(image_metrics["visible_rows"])
        img_start = self.image_scroll_offset
        img_end = min(len(self.image_names), img_start + visible_img_rows)

        if int(image_metrics["max_y_offset"]) > 0:
            status_text = f"{img_start + 1}-{img_end} / {len(self.image_names)}"
            status_w = self._text_width(status_text, 0.46, 1)
            self._put_text(
                panel,
                status_text,
                (ix2 - status_w - 6, iy1 - 8),
                0.46,
                (80, 80, 80),
                1,
            )
        self._draw_list_contents(panel, "image", image_metrics)

        # Footer help area.
        help_top = self.class_panel_h - footer_h
        help_bottom = self.class_panel_h - outer_pad
        cv2.rectangle(panel, (outer_pad, help_top), (self.class_panel_width - outer_pad, help_bottom), (210, 210, 210), 1)
        btn_x1 = outer_pad + 8
        btn_y1 = help_top + 10
        btn_x2 = self.class_panel_width - outer_pad - 8
        btn_y2 = btn_y1 + 36
        self.save_dataset_button_rect = (btn_x1, btn_y1, btn_x2, btn_y2)
        cv2.rectangle(panel, (btn_x1, btn_y1), (btn_x2, btn_y2), (28, 66, 135), -1)
        cv2.rectangle(panel, (btn_x1, btn_y1), (btn_x2, btn_y2), (18, 45, 95), 1)
        button_label = "保存数据集"
        button_text_w = self._text_width(button_label, 0.62, 2)
        button_text_h = self._font_size(0.62)
        button_text_x = btn_x1 + max(0, (btn_x2 - btn_x1 - button_text_w) // 2)
        button_text_y = btn_y1 + max(button_text_h + 4, (btn_y2 - btn_y1 + button_text_h) // 2)
        self._put_text(
            panel,
            button_label,
            (button_text_x, button_text_y),
            0.62,
            (255, 255, 255),
            2,
        )

        help_text_top = btn_y2 + 24
        self._put_text(panel, "快捷键：", (16, help_text_top), 0.5, (40, 40, 40), 1)
        self._put_text(panel, "a / d：切换类别", (16, help_text_top + 22), 0.5, (50, 50, 50), 1)
        self._put_text(panel, "s：保存当前图片", (16, help_text_top + 42), 0.5, (50, 50, 50), 1)
        self._put_text(panel, "n：新建类别 | u：撤销", (16, help_text_top + 62), 0.5, (50, 50, 50), 1)
        self._put_text(panel, "q / Esc：退出", (16, help_text_top + 82), 0.5, (50, 50, 50), 1)
        self._put_text(panel, "双击图片：保存并切换", (16, help_text_top + 104), 0.45, (50, 50, 50), 1)

        input_top = header_h
        input_bottom = header_h + input_h - 4
        if self.adding_new_class:
            cv2.rectangle(panel, (10, input_top), (self.class_panel_width - 10, input_bottom), (230, 245, 255), -1)
            cv2.rectangle(panel, (10, input_top), (self.class_panel_width - 10, input_bottom), (120, 160, 190), 1)
            input_max_w = self.class_panel_width - 28
            input_prefix = "新类别："
            input_suffix = "_"
            reserved_w = self._text_width(
                input_prefix + input_suffix,
                0.50,
                1,
            )
            name_text = self._truncate_text(
                self.new_class_buffer,
                max(40, input_max_w - reserved_w),
                0.50,
                1,
            )
            input_text = f"{input_prefix}{name_text}{input_suffix}"
            hint_text = self._truncate_text(
                "Enter 确认 | Backspace 删除 | Esc 取消",
                input_max_w,
                0.42,
                1,
            )
            self._put_text(
                panel,
                input_text,
                (16, input_top + 23),
                0.50,
                (30, 90, 120),
                1,
            )
            self._put_text(
                panel,
                hint_text,
                (16, input_top + 46),
                0.42,
                (30, 90, 120),
                1,
            )

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

            if self.save_dataset_requested:
                cv2.destroyAllWindows()
                return self.annotations

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

            if key == ord("a") and self.class_names:
                self.current_class_idx = (self.current_class_idx - 1) % len(self.class_names)
                self._ensure_selected_visible()
            elif key == ord("d") and self.class_names:
                self.current_class_idx = (self.current_class_idx + 1) % len(self.class_names)
                self._ensure_selected_visible()
            elif key == ord("n"):
                self.adding_new_class = True
                self.new_class_buffer = ""
            elif key == ord("u") and self.annotations:
                self.annotations.pop()
            elif key == ord("s"):
                cv2.destroyAllWindows()
                return self.annotations
            elif key == ord("q") or key == 27:
                cv2.destroyAllWindows()
                return None
