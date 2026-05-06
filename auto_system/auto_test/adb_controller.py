import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class AdbController:
    """
    ADB wrapper + XML operation simulator.

    - simulate=True: do not send real adb operations, only print and record operations.
    - simulate=False: execute real adb commands when possible.
    """

    KEY_MAP = {
        "HOME": "3",
        "BACK": "4",
        "VOLUME_UP": "24",
        "VOLUME_DOWN": "25",
        "POWER": "26",
        "ENTER": "66",
    }

    def __init__(self, device_serial: Optional[str] = None, simulate: bool = True):
        self.device_serial = device_serial
        self.simulate = simulate
        self.operation_history: List[Dict[str, Any]] = []
        self.screen_source = "adb"
        self.model_controller = None
        self.image_resources: Dict[str, Dict[str, str]] = {}
        self.image_resource_base_dir: Optional[Path] = None
        self._device_size_cache: Optional[Tuple[int, int]] = None

        # Mock state for assert simulation.
        self.mock_image_visibility: Dict[str, bool] = {}
        self.mock_text_presence: Dict[str, bool] = {}
        self.mock_current_page: str = ""

    def set_model_controller(self, model_controller: Any) -> None:
        self.model_controller = model_controller

    def set_image_resources(
        self,
        image_resources: Dict[str, Dict[str, str]],
        base_dir: Optional[str] = None,
    ) -> None:
        self.image_resources = image_resources or {}
        self.image_resource_base_dir = Path(base_dir).resolve() if base_dir else None

    def set_screen_source(self, screen_source: str) -> None:
        value = str(screen_source or "adb").strip().lower()
        self.screen_source = value if value in {"adb", "desktop"} else "adb"

    # -----------------------------
    # Basic ADB helpers
    # -----------------------------
    def _build_adb_prefix(self, device_serial: Optional[str] = None) -> List[str]:
        serial = device_serial or self.device_serial
        cmd = ["adb"]
        if serial:
            cmd += ["-s", serial]
        return cmd

    def _adb_available(self) -> bool:
        return shutil.which("adb") is not None

    def run_adb_command(
        self, cmd: List[str], timeout: int = 10, binary: bool = False
    ) -> Tuple[Optional[Any], str]:
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            stdout = result.stdout if binary else result.stdout.decode("utf-8", errors="ignore").strip()
            stderr = result.stderr.decode("utf-8", errors="ignore").strip()
            if result.returncode != 0:
                return None, stderr or f"adb command failed, return code={result.returncode}"
            return stdout, stderr
        except subprocess.TimeoutExpired:
            return None, f"adb command timeout ({timeout}s)"
        except Exception as e:
            return None, f"adb command exception: {e}"

    def get_connected_devices(self) -> List[str]:
        if not self._adb_available():
            return []
        stdout, stderr = self.run_adb_command(["adb", "devices"])
        if stdout is None:
            print(f"[ADB] get devices failed: {stderr}")
            return []

        devices: List[str] = []
        lines = str(stdout).splitlines()[1:]
        for line in lines:
            if "\t" in line:
                serial, status = line.split("\t", 1)
                if status.strip() == "device":
                    devices.append(serial.strip())
        return devices

    def catch_screen(self, save_path: str, device_serial: Optional[str] = None) -> bool:
        if self.simulate:
            print(f"[SIM] catch_screen skipped in simulate mode: {save_path}")
            return False
        if not self._adb_available():
            print("[ADB] adb not found in PATH.")
            return False

        cmd = self._build_adb_prefix(device_serial) + ["exec-out", "screencap", "-p"]
        stdout, stderr = self.run_adb_command(cmd, timeout=20, binary=True)
        if stdout is None:
            print(f"[ADB] screenshot failed: {stderr}")
            return False

        data: bytes = stdout.replace(b"\r\n", b"\n")
        save_file = Path(save_path)
        save_file.parent.mkdir(parents=True, exist_ok=True)
        save_file.write_bytes(data)
        print(f"[ADB] screenshot saved: {save_file}")
        return True

    def catch_desktop_screen(self, save_path: str) -> bool:
        try:
            from PIL import ImageGrab
        except ImportError:
            print("[DESKTOP] Pillow is required for desktop capture: pip install pillow")
            return False

        try:
            image = ImageGrab.grab(all_screens=True)
            save_file = Path(save_path)
            save_file.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(save_file))
            print(f"[DESKTOP] screenshot saved: {save_file}")
            return True
        except Exception as e:
            print(f"[DESKTOP] screenshot failed: {e}")
            return False

    def adb_tap(self, x: int, y: int, device_serial: Optional[str] = None) -> bool:
        if self.simulate:
            print(f"[SIM] tap ({x}, {y})")
            return True
        if not self._adb_available():
            print("[ADB] adb not found in PATH.")
            return False

        cmd = self._build_adb_prefix(device_serial) + ["shell", "input", "tap", str(x), str(y)]
        _, stderr = self.run_adb_command(cmd)
        if stderr:
            print(f"[ADB] tap failed: {stderr}")
            return False
        print(f"[ADB] tap ({x}, {y})")
        return True

    def adb_swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: int = 500,
        device_serial: Optional[str] = None,
    ) -> bool:
        if self.simulate:
            print(f"[SIM] swipe ({x1}, {y1}) -> ({x2}, {y2}), duration={duration}ms")
            return True
        if not self._adb_available():
            print("[ADB] adb not found in PATH.")
            return False

        cmd = self._build_adb_prefix(device_serial) + [
            "shell",
            "input",
            "swipe",
            str(x1),
            str(y1),
            str(x2),
            str(y2),
            str(duration),
        ]
        _, stderr = self.run_adb_command(cmd)
        if stderr:
            print(f"[ADB] swipe failed: {stderr}")
            return False
        print(f"[ADB] swipe ({x1}, {y1}) -> ({x2}, {y2})")
        return True

    def adb_press_key(self, key: str, device_serial: Optional[str] = None) -> bool:
        key_code = self.KEY_MAP.get(str(key).upper(), str(key))
        if self.simulate:
            print(f"[SIM] press_key {key} ({key_code})")
            return True
        if not self._adb_available():
            print("[ADB] adb not found in PATH.")
            return False

        cmd = self._build_adb_prefix(device_serial) + ["shell", "input", "keyevent", key_code]
        _, stderr = self.run_adb_command(cmd)
        if stderr:
            print(f"[ADB] press key failed: {stderr}")
            return False
        print(f"[ADB] press_key {key} ({key_code})")
        return True

    # -----------------------------
    # XML operation simulation APIs
    # -----------------------------
    def set_mock_image_state(self, image_id: str, visible: bool) -> None:
        self.mock_image_visibility[image_id] = visible

    def set_mock_text_state(self, text: str, exists: bool) -> None:
        self.mock_text_presence[text] = exists

    def set_mock_current_page(self, page_name: str) -> None:
        self.mock_current_page = page_name

    def wait(self, duration: int) -> bool:
        ms = max(int(duration), 0)
        if self.simulate:
            print(f"[SIM] wait {ms}ms")
            # keep simulation fast
            time.sleep(min(ms / 1000.0, 0.1))
            return True
        time.sleep(ms / 1000.0)
        return True

    def click_image(
        self,
        image_id: str,
        image_positions: Optional[Dict[str, Tuple[int, int]]] = None,
        on_page_image_id: str = "",
    ) -> bool:
        detection_bundle = self._detect_target(image_id=image_id, on_page_image_id=on_page_image_id)
        if detection_bundle is not None:
            target = detection_bundle["target"]
            center = target["center"]
            tap_x, tap_y = int(center["x"]), int(center["y"])
            if self.screen_source == "desktop" and not self.simulate:
                mapped = self._map_desktop_point_to_device(
                    point=(tap_x, tap_y),
                    page_detection=detection_bundle.get("page"),
                    screen_size=detection_bundle.get("screen_size"),
                )
                if mapped is None:
                    print(
                        "[DETECT] click_image failed: cannot map desktop coordinate to device. "
                        "Provide a reliable onPageImageId or use adb screen source."
                    )
                    return False
                tap_x, tap_y = mapped
            print(
                f"[DETECT] click_image '{image_id}' -> {target['class_name']} "
                f"conf={target['confidence']:.3f} center=({center['x']},{center['y']}) "
                f"tap=({tap_x},{tap_y})"
            )
            return self.adb_tap(tap_x, tap_y)
        print(
            f"[DETECT] click_image '{image_id}' not found."
            + (f" page='{on_page_image_id}'" if on_page_image_id else "")
        )
        return False

    def click_coordinate(self, x: int, y: int) -> bool:
        return self.adb_tap(int(x), int(y))

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> bool:
        return self.adb_swipe(int(start_x), int(start_y), int(end_x), int(end_y), int(duration))

    def press_key(self, key: str) -> bool:
        return self.adb_press_key(key)

    def verify_image(
        self,
        image_id: str,
        expected_state: str = "visible",
        timeout: int = 5000,
        on_page_image_id: str = "",
    ) -> bool:
        found = self._wait_model_detect(
            image_id=image_id,
            timeout=timeout,
            on_page_image_id=on_page_image_id,
        )
        expect_visible = str(expected_state).lower() == "visible"
        ok = (found is not None) == expect_visible
        print(
            f"[ASSERT] verify_image imageId={image_id} expected={expected_state} "
            f"found={found is not None}"
            + (f" onPageImageId={on_page_image_id}" if on_page_image_id else "")
            + f" -> {'PASS' if ok else 'FAIL'}"
        )
        return ok

    def verify_text(self, region: Dict[str, int], text: str, timeout: int = 2000) -> bool:
        # Current version uses mock text state. Future: replace by OCR in region.
        start = time.time()
        timeout_s = max(int(timeout), 0) / 1000.0

        while True:
            exists = self.mock_text_presence.get(text, True if self.simulate else False)
            if exists:
                print(f"[ASSERT] verify_text text='{text}' region={region} -> PASS")
                return True

            if (time.time() - start) >= timeout_s:
                print(f"[ASSERT] verify_text text='{text}' region={region} -> FAIL")
                return False
            time.sleep(0.1)

    def verify_image_present(
        self,
        image_id: str,
        timeout: int = 3000,
        on_page_image_id: str = "",
    ) -> bool:
        # "Image present in current page" is equivalent to a visible-state image check.
        return self.verify_image(
            image_id=image_id,
            expected_state="visible",
            timeout=timeout,
            on_page_image_id=on_page_image_id,
        )

    def verify_page(
        self,
        page_name: str = "",
        page_image_id: str = "",
        timeout: int = 3000,
    ) -> bool:
        if not page_image_id:
            print("[ASSERT] verify_page failed: pageImageId is required for model-based page verification.")
            return False
        return self.verify_image_present(image_id=page_image_id, timeout=timeout)

    def _wait_model_detect(
        self,
        image_id: str,
        timeout: int,
        on_page_image_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        timeout_s = max(int(timeout), 0) / 1000.0
        started = time.time()
        while True:
            detection = self._detect_target(
                image_id=image_id,
                on_page_image_id=on_page_image_id,
            )
            if detection is not None:
                return detection
            if (time.time() - started) >= timeout_s:
                return None
            time.sleep(0.15)

    def _detect_target(
        self,
        image_id: str,
        on_page_image_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        screen_path = self._capture_for_detection()
        if not screen_path:
            return None
        detections = self._infer_screen_detections(screen_path) if self.model_controller is not None else []

        page_detection: Optional[Dict[str, Any]] = None
        if on_page_image_id:
            page_labels = self._build_target_labels(on_page_image_id)
            page_detection = self._pick_best_detection(detections, page_labels, region=None)
            if page_detection is None:
                page_detection = self._match_image_resource(screen_path, on_page_image_id, region=None)
            if page_detection is None:
                return None

        labels = self._build_target_labels(image_id)
        region = page_detection.get("bbox") if page_detection else None
        target_detection = self._pick_best_detection(detections, labels, region=region)
        if target_detection is None:
            target_detection = self._match_image_resource(screen_path, image_id, region=region)
        if target_detection is None:
            return None

        return {
            "target": target_detection,
            "page": page_detection,
            "screen_size": self._read_image_size(screen_path),
        }

    def _resolve_image_resource_path(self, image_id: str) -> Optional[Path]:
        resource = self.image_resources.get(image_id, {}) or {}
        raw_path = str(resource.get("path", "")).strip()
        if not raw_path:
            return None
        path = Path(raw_path)
        candidates = []
        if path.is_absolute():
            candidates.append(path)
        else:
            if self.image_resource_base_dir is not None:
                candidates.append(self.image_resource_base_dir / path)
            candidates.append(Path.cwd() / path)
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                resolved = candidate
            if resolved.exists():
                return resolved
        return None

    def _template_scales(self, search_w: int, search_h: int, template_w: int, template_h: int) -> List[float]:
        base_scales = [1.0, 0.95, 1.05, 0.9, 1.1, 0.85, 1.15, 0.8, 1.2, 0.75, 1.25, 0.7, 1.3]
        scales: List[float] = []
        for scale in base_scales:
            w = int(template_w * scale)
            h = int(template_h * scale)
            if w < 8 or h < 8 or w > search_w or h > search_h:
                continue
            if scale not in scales:
                scales.append(scale)
        return scales

    def _match_image_resource(
        self,
        screen_path: Path,
        image_id: str,
        region: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        template_path = self._resolve_image_resource_path(image_id)
        if template_path is None:
            return None
        try:
            import cv2
        except ImportError:
            print("[DETECT] template matching requires opencv-python.")
            return None

        screen = cv2.imread(str(screen_path), cv2.IMREAD_COLOR)
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if screen is None or template is None:
            return None

        offset_x = 0
        offset_y = 0
        search = screen
        if region is not None:
            bbox = region or {}
            x1 = max(int(bbox.get("x1", 0)), 0)
            y1 = max(int(bbox.get("y1", 0)), 0)
            x2 = min(int(bbox.get("x2", screen.shape[1])), screen.shape[1])
            y2 = min(int(bbox.get("y2", screen.shape[0])), screen.shape[0])
            if x2 <= x1 or y2 <= y1:
                return None
            search = screen[y1:y2, x1:x2]
            offset_x = x1
            offset_y = y1

        search_gray = cv2.cvtColor(search, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        search_h, search_w = search_gray.shape[:2]
        template_h, template_w = template_gray.shape[:2]
        scales = self._template_scales(search_w, search_h, template_w, template_h)
        if not scales:
            return None

        best_score = -1.0
        best_loc = (0, 0)
        best_size = (0, 0)
        for scale in scales:
            scaled_w = int(template_w * scale)
            scaled_h = int(template_h * scale)
            if scale == 1.0:
                candidate = template_gray
            else:
                candidate = cv2.resize(template_gray, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            result = cv2.matchTemplate(search_gray, candidate, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if float(max_val) > best_score:
                best_score = float(max_val)
                best_loc = max_loc
                best_size = (scaled_w, scaled_h)

        area_ratio = (best_size[0] * best_size[1]) / float(max(search_w * search_h, 1))
        threshold = 0.62 if area_ratio >= 0.25 else 0.72
        if best_score < threshold:
            return None

        x1 = offset_x + int(best_loc[0])
        y1 = offset_y + int(best_loc[1])
        x2 = x1 + int(best_size[0])
        y2 = y1 + int(best_size[1])
        print(
            f"[DETECT] template '{image_id}' -> {template_path.name} "
            f"score={best_score:.3f} bbox=({x1},{y1},{x2},{y2})"
        )
        return {
            "class_idx": -1,
            "class_name": image_id,
            "confidence": best_score,
            "source": "template",
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "center": {"x": int((x1 + x2) / 2), "y": int((y1 + y2) / 2)},
        }

    def _infer_screen_detections(self, screen_path: Path) -> List[Dict[str, Any]]:
        infer_fn = getattr(self.model_controller, "infer", None)
        if callable(infer_fn):
            try:
                return list(infer_fn(str(screen_path)) or [])
            except Exception as e:
                print(f"[DETECT] infer failed: {e}")
                return []

        # Compatibility fallback if only find_target exists on custom model controller.
        detections: List[Dict[str, Any]] = []
        find_fn = getattr(self.model_controller, "find_target", None)
        if callable(find_fn):
            labels = self._build_target_labels("")
            best = find_fn(str(screen_path), labels)
            if best:
                detections.append(best)
        return detections

    def _pick_best_detection(
        self,
        detections: List[Dict[str, Any]],
        labels: List[str],
        region: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not detections or not labels:
            return None
        exact_labels: List[str] = []
        fuzzy_labels: List[str] = []
        for item in labels:
            raw = str(item)
            exact = self._normalize_label_exact(raw)
            fuzzy = self._normalize_label(raw)
            if exact and exact not in exact_labels:
                exact_labels.append(exact)
            if fuzzy and fuzzy not in fuzzy_labels:
                fuzzy_labels.append(fuzzy)
        if not exact_labels and not fuzzy_labels:
            return None
        exact_rank = {name: idx for idx, name in enumerate(exact_labels)}
        fuzzy_rank = {name: idx for idx, name in enumerate(fuzzy_labels)}

        best: Optional[Dict[str, Any]] = None
        best_rank = 10**9
        for det in detections:
            det_name = str(det.get("class_name", ""))
            det_exact = self._normalize_label_exact(det_name)
            det_fuzzy = self._normalize_label(det_name)

            if det_exact in exact_rank:
                rank = exact_rank[det_exact]
            elif det_fuzzy in fuzzy_rank:
                rank = len(exact_labels) + fuzzy_rank[det_fuzzy]
            else:
                continue
            if region is not None and not self._is_center_in_region(det, region):
                continue
            conf = float(det.get("confidence", 0.0))
            if best is None:
                best = det
                best_rank = rank
                continue
            best_conf = float(best.get("confidence", 0.0))
            if rank < best_rank or (rank == best_rank and conf > best_conf):
                best = det
                best_rank = rank
        return best

    def _is_center_in_region(self, detection: Dict[str, Any], region: Dict[str, Any]) -> bool:
        center = detection.get("center", {}) or {}
        x = int(center.get("x", -1))
        y = int(center.get("y", -1))
        x1 = int(region.get("x1", 0))
        y1 = int(region.get("y1", 0))
        x2 = int(region.get("x2", 0))
        y2 = int(region.get("y2", 0))
        return x1 <= x <= x2 and y1 <= y <= y2

    def _normalize_label(self, label: str) -> str:
        normalized = self._normalize_label_exact(label)
        normalized = normalized.replace("-", "_").replace(" ", "_")
        for suffix in ("_icon", "_button", "_btn", "_panel", "_page"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        return normalized

    def _normalize_label_exact(self, label: str) -> str:
        return label.lower().strip().replace("-", "_").replace(" ", "_")

    def _read_image_size(self, image_path: Path) -> Optional[Tuple[int, int]]:
        try:
            from PIL import Image

            with Image.open(str(image_path)) as img:
                return int(img.width), int(img.height)
        except Exception:
            return None

    def _get_device_size(self) -> Optional[Tuple[int, int]]:
        if self._device_size_cache is not None:
            return self._device_size_cache
        if self.simulate or not self._adb_available():
            return None

        cmd = self._build_adb_prefix() + ["shell", "wm", "size"]
        stdout, _ = self.run_adb_command(cmd, timeout=5)
        if stdout is None:
            return None
        text = str(stdout)
        # expected: "Physical size: 1080x1920"
        for line in text.splitlines():
            if "size" in line and "x" in line:
                parts = line.split(":")
                right = parts[-1].strip() if parts else line.strip()
                wh = right.lower().replace(" ", "")
                if "x" not in wh:
                    continue
                w_str, h_str = wh.split("x", 1)
                if w_str.isdigit() and h_str.isdigit():
                    self._device_size_cache = (int(w_str), int(h_str))
                    return self._device_size_cache
        return None

    def _map_desktop_point_to_device(
        self,
        point: Tuple[int, int],
        page_detection: Optional[Dict[str, Any]],
        screen_size: Optional[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        device_size = self._get_device_size()
        if device_size is None:
            return None
        dev_w, dev_h = device_size

        if page_detection is not None:
            bbox = page_detection.get("bbox", {}) or {}
            x1 = int(bbox.get("x1", 0))
            y1 = int(bbox.get("y1", 0))
            x2 = int(bbox.get("x2", 0))
            y2 = int(bbox.get("y2", 0))
            src_w = max(x2 - x1, 1)
            src_h = max(y2 - y1, 1)
            rel_x = (point[0] - x1) / float(src_w)
            rel_y = (point[1] - y1) / float(src_h)
        elif screen_size is not None:
            src_w = max(int(screen_size[0]), 1)
            src_h = max(int(screen_size[1]), 1)
            rel_x = point[0] / float(src_w)
            rel_y = point[1] / float(src_h)
        else:
            return None

        rel_x = min(max(rel_x, 0.0), 1.0)
        rel_y = min(max(rel_y, 0.0), 1.0)
        mapped_x = min(max(int(round(rel_x * dev_w)), 0), dev_w - 1)
        mapped_y = min(max(int(round(rel_y * dev_h)), 0), dev_h - 1)
        return mapped_x, mapped_y

    def _build_target_labels(self, image_id: str) -> List[str]:
        labels = [image_id]
        labels.append(image_id.replace("_icon", ""))
        labels.append(image_id.replace("_button", ""))
        labels.append(image_id.replace("_btn", ""))
        labels.append(image_id.replace("_panel", ""))
        labels.append(image_id.replace("_page", ""))

        resource = self.image_resources.get(image_id, {})
        for key in ("className", "class_name", "modelClass", "model_class", "label", "aliases"):
            value = str(resource.get(key, "")).strip()
            if value:
                normalized = value.replace(";", ",").replace("|", ",")
                labels.extend(part.strip() for part in normalized.split(","))
        img_path = resource.get("path", "")
        if img_path:
            labels.append(Path(img_path).stem)
        desc = resource.get("description", "")
        if desc:
            labels.extend(str(desc).lower().replace("-", " ").split())

        # de-duplicate while preserving order
        uniq: List[str] = []
        seen = set()
        for x in labels:
            val = str(x).strip()
            if not val:
                continue
            if val in seen:
                continue
            seen.add(val)
            uniq.append(val)
        return uniq

    def _capture_for_detection(self) -> Optional[Path]:
        tmp = tempfile.NamedTemporaryFile(prefix="screen_", suffix=".png", delete=False)
        tmp.close()
        p = Path(tmp.name)
        if self.screen_source == "desktop":
            ok = self.catch_desktop_screen(str(p))
        else:
            ok = self.catch_screen(str(p))
        return p if ok else None

    # -----------------------------
    # Generic runner for parsed XML step items
    # -----------------------------
    def execute_operation(
        self,
        operation: Dict[str, Any],
        image_positions: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> bool:
        category = operation.get("category", "").lower()
        op_type = operation.get("type", "").lower()
        params = operation.get("params", {}) or {}

        self.operation_history.append(
            {"category": category, "type": op_type, "params": dict(params)}
        )

        if category == "action":
            if op_type == "click_image":
                return self.click_image(
                    str(params.get("imageId", "")),
                    image_positions=image_positions,
                    on_page_image_id=str(params.get("onPageImageId", "")),
                )
            if op_type == "click_coordinate":
                return self.click_coordinate(int(params.get("x", 0)), int(params.get("y", 0)))
            if op_type == "swipe":
                return self.swipe(
                    int(params.get("startX", 0)),
                    int(params.get("startY", 0)),
                    int(params.get("endX", 0)),
                    int(params.get("endY", 0)),
                    int(params.get("duration", 500)),
                )
            if op_type == "press_key":
                return self.press_key(str(params.get("key", "")))
            if op_type == "wait":
                return self.wait(int(params.get("duration", 0)))
            print(f"[WARN] unsupported action type: {op_type}")
            return False

        if category == "assert":
            if op_type == "verify_image":
                return self.verify_image(
                    image_id=str(params.get("imageId", "")),
                    expected_state=str(params.get("expectedState", "visible")),
                    timeout=int(params.get("timeout", 5000)),
                    on_page_image_id=str(params.get("onPageImageId", "")),
                )
            if op_type == "verify_text":
                return self.verify_text(
                    region=params.get("region", {}),
                    text=str(params.get("text", "")),
                    timeout=int(params.get("timeout", 2000)),
                )
            if op_type == "verify_image_present":
                return self.verify_image_present(
                    image_id=str(params.get("imageId", "")),
                    timeout=int(params.get("timeout", 3000)),
                    on_page_image_id=str(params.get("onPageImageId", "")),
                )
            if op_type == "verify_page":
                return self.verify_page(
                    page_name=str(params.get("pageName", "")),
                    page_image_id=str(params.get("pageImageId", "")),
                    timeout=int(params.get("timeout", 3000)),
                )
            print(f"[WARN] unsupported assert type: {op_type}")
            return False

        print(f"[WARN] unsupported operation category: {category}")
        return False

    def execute_step(
        self,
        step: Dict[str, Any],
        image_positions: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> bool:
        step_id = step.get("id", "")
        step_name = step.get("name", "")
        print(f"[STEP] {step_id} {step_name}")
        for op in step.get("actions", []):
            ok = self.execute_operation(op, image_positions=image_positions)
            if not ok:
                print(f"[STEP] failed at op: {op}")
                return False
        return True

    def execute_test_case(
        self,
        test_case: Dict[str, Any],
        image_positions: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> bool:
        print(f"[CASE] {test_case.get('id', '')} {test_case.get('name', '')}")
        for step in test_case.get("steps", []):
            if not self.execute_step(step, image_positions=image_positions):
                return False
        return True


if __name__ == "__main__":
    # Quick local demo in simulate mode.
    controller = AdbController(simulate=True)
    sample_step = {
        "id": "1",
        "name": "Demo step",
        "actions": [
            {"category": "action", "type": "click_coordinate", "params": {"x": 100, "y": 200}},
            {"category": "action", "type": "wait", "params": {"duration": 300}},
            {
                "category": "assert",
                "type": "verify_image",
                "params": {"imageId": "home_icon", "expectedState": "visible", "timeout": 1000},
            },
        ],
    }
    controller.set_mock_image_state("home_icon", True)
    ok = controller.execute_step(sample_step)
    print(f"[RESULT] execute_step={ok}")
