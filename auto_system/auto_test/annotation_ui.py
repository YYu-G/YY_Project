import cv2
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
        max_window_size: Tuple[int, int] = (1400, 900),
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
        self.display_scale = min(max_w / self.image_w, max_h / self.image_h, 1.0)
        self.display_w = max(1, int(self.image_w * self.display_scale))
        self.display_h = max(1, int(self.image_h * self.display_scale))

        self.display_image = self.image.copy()
        self.window_name = "YOLO Annotation Tool"

        self.drawing = False
        self.start_point: Optional[Tuple[int, int]] = None
        self.current_bbox: Optional[List[int]] = None
        self.adding_new_class = False
        self.new_class_buffer = ""

    def _to_original(self, x: int, y: int) -> Tuple[int, int]:
        ox = int(round(x / self.display_scale))
        oy = int(round(y / self.display_scale))
        ox = max(0, min(self.image_w - 1, ox))
        oy = max(0, min(self.image_h - 1, oy))
        return ox, oy

    def _to_display(self, x: int, y: int) -> Tuple[int, int]:
        dx = int(round(x * self.display_scale))
        dy = int(round(y * self.display_scale))
        dx = max(0, min(self.display_w - 1, dx))
        dy = max(0, min(self.display_h - 1, dy))
        return dx, dy

    def _mouse_callback(self, event, x, y, flags, param):
        if self.adding_new_class:
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

        tips = (
            f"class: {self.class_names[self.current_class_idx]} | "
            "a/d switch | n new class | u undo | s save | q quit"
        )
        cv2.putText(
            canvas,
            tips,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2,
        )

        if self.display_scale < 1.0:
            cv2.putText(
                canvas,
                f"scale: {self.display_scale:.2f} (auto-fit)",
                (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2,
            )

        if self.adding_new_class:
            cv2.putText(
                canvas,
                f"new class: {self.new_class_buffer}_",
                (10, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.putText(
                canvas,
                "Enter confirm | Backspace delete | Esc cancel",
                (10, 115),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

        if self.display_scale != 1.0:
            self.display_image = cv2.resize(
                canvas, (self.display_w, self.display_h), interpolation=cv2.INTER_AREA
            )
        else:
            self.display_image = canvas

    def run(self) -> Optional[List[Dict]]:
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.display_w, self.display_h)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        while True:
            self._draw()
            cv2.imshow(self.window_name, self.display_image)
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
            elif key == ord("d"):
                self.current_class_idx = (self.current_class_idx + 1) % len(self.class_names)
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
