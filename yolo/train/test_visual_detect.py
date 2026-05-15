import argparse
import os
from typing import List, Optional, Set

import cv2
from ultralytics import YOLO


def choose_file_dialog(title: str, filetypes) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return path or None


def parse_targets(raw: str) -> Set[str]:
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def draw_result(frame, result, names: dict, target_names: Set[str], conf_thr: float):
    boxes = result.boxes
    if boxes is None:
        return frame

    for box in boxes:
        conf = float(box.conf[0])
        if conf < conf_thr:
            continue
        cls_id = int(box.cls[0])
        cls_name = str(names.get(cls_id, cls_id))

        if target_names and cls_name not in target_names:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        is_target = cls_name in target_names if target_names else True
        color = (0, 255, 0) if is_target else (255, 200, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{cls_name} {conf:.2f}"
        cv2.putText(
            frame,
            label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )
    return frame


def run_image(model: YOLO, source: str, target_names: Set[str], conf_thr: float, save_path: Optional[str]):
    img = cv2.imread(source)
    if img is None:
        raise RuntimeError(f"Failed to load image: {source}")

    result = model.predict(source=img, conf=conf_thr, verbose=False)[0]
    out = draw_result(img.copy(), result, model.names, target_names, conf_thr)

    if save_path:
        cv2.imwrite(save_path, out)
        print(f"Saved result: {save_path}")

    # Fit preview window to screen while keeping aspect ratio.
    screen_w, screen_h = 1600, 900
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_w = max(800, int(root.winfo_screenwidth() * 0.9))
        screen_h = max(600, int(root.winfo_screenheight() * 0.9))
        root.destroy()
    except Exception:
        pass

    h, w = out.shape[:2]
    scale = min(screen_w / max(1, w), screen_h / max(1, h), 1.0)
    preview = out if scale >= 1.0 else cv2.resize(out, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    cv2.namedWindow("YOLO Visual Detect (image)", cv2.WINDOW_NORMAL)
    cv2.imshow("YOLO Visual Detect (image)", preview)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_video(model: YOLO, source: str, target_names: Set[str], conf_thr: float):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video/source: {source}")

    print("Press 'q' to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        result = model.predict(source=frame, conf=conf_thr, verbose=False)[0]
        out = draw_result(frame, result, model.names, target_names, conf_thr)
        cv2.imshow("YOLO Visual Detect (video)", out)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Visual test: choose model + target class and show detection boxes.")
    parser.add_argument("--model", default="", help="Path to model .pt")
    parser.add_argument("--source", default="", help="Path to image/video, or webcam index like 0")
    parser.add_argument("--target", default="", help="Target class names, comma-separated. Example: home_btn,music_btn")
    parser.add_argument("--conf", type=float, default=0.2, help="Confidence threshold, default 0.2")
    parser.add_argument("--save", default="", help="Optional output image path when source is image")
    args = parser.parse_args()

    model_path = args.model.strip()
    if not model_path:
        model_path = choose_file_dialog(
            "Select YOLO model (.pt)",
            [("PyTorch Model", "*.pt"), ("All Files", "*.*")],
        ) or ""
    if not model_path:
        raise SystemExit("No model selected.")
    if not os.path.isfile(model_path):
        raise SystemExit(f"Model not found: {model_path}")

    source = args.source.strip()
    if not source:
        source = choose_file_dialog(
            "Select image/video source",
            [
                ("Media", "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.mp4;*.avi;*.mov;*.mkv"),
                ("All Files", "*.*"),
            ],
        ) or ""
    if not source:
        raise SystemExit("No source selected.")

    target_names = parse_targets(args.target)

    model = YOLO(model_path)
    print(f"Model: {model_path}")
    print(f"Available classes: {model.names}")
    print(f"Target classes: {sorted(target_names) if target_names else 'ALL'}")
    print(f"Conf threshold: {args.conf}")

    is_webcam = source.isdigit()
    is_video = source.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
    if is_webcam:
        run_video(model, int(source), target_names, args.conf)
    elif is_video:
        run_video(model, source, target_names, args.conf)
    else:
        run_image(model, source, target_names, args.conf, args.save.strip() or None)


if __name__ == "__main__":
    main()
