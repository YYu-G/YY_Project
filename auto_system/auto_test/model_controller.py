from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from model_trainer import ModelTrainer


class ModelController:
    """
    Unified entry for model-related capabilities:
    1) dataset annotation/export + model training
    2) model loading + inference + target lookup
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf: float = 0.25,
        iou: float = 0.7,
        device: str = "cpu",
        dataset_name: str = "custom_dataset",
        datasets_root: Optional[str] = None,
    ) -> None:
        self.model_path = model_path
        self.conf = conf
        self.iou = iou
        self.device = device
        self.model = None

        # Training/dataset orchestrator
        self.trainer = ModelTrainer(dataset_name=dataset_name, datasets_root=datasets_root)

        # Optional immediate inference model load
        if model_path:
            self.load_model(model_path)

    # -----------------------------
    # Training/dataset methods
    # -----------------------------
    def create_dataset_with_annotation(
        self,
        raw_image_dir: str,
        class_names: Optional[List[str]] = None,
        classes_file: Optional[str] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        seed: int = 42,
        skip_unlabeled: bool = False,
    ) -> Dict[str, Any]:
        return self.trainer.create_dataset_with_annotation(
            raw_image_dir=raw_image_dir,
            class_names=class_names,
            classes_file=classes_file,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
            skip_unlabeled=skip_unlabeled,
        )

    def train_model(
        self,
        dataset_yaml: str,
        model_weights: str = "yolo11n.pt",
        epochs: int = 100,
        imgsz: int = 640,
        batch: int = 16,
        device: str = "cpu",
        workers: int = 4,
        run_name: str = "result",
        exist_ok: bool = True,
        auto_load_best: bool = True,
    ) -> Dict[str, Any]:
        result = self.trainer.train_model(
            dataset_yaml=dataset_yaml,
            model_weights=model_weights,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            workers=workers,
            run_name=run_name,
            exist_ok=exist_ok,
        )
        if auto_load_best and result.get("fixed_best_model"):
            best_model = str(result["fixed_best_model"])
            if Path(best_model).exists():
                self.load_model(best_model)
        return result

    def build_and_train(
        self,
        raw_image_dir: str,
        class_names: Optional[List[str]] = None,
        classes_file: Optional[str] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        seed: int = 42,
        skip_unlabeled: bool = False,
        model_weights: str = "yolo11n.pt",
        epochs: int = 100,
        imgsz: int = 640,
        batch: int = 16,
        train_device: str = "cpu",
        workers: int = 4,
        run_name: str = "result",
        exist_ok: bool = True,
        auto_load_best: bool = True,
    ) -> Dict[str, Any]:
        dataset_result = self.create_dataset_with_annotation(
            raw_image_dir=raw_image_dir,
            class_names=class_names,
            classes_file=classes_file,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
            skip_unlabeled=skip_unlabeled,
        )
        if not dataset_result.get("success"):
            return {
                "success": False,
                "stage": "dataset",
                "dataset_result": dataset_result,
            }

        train_result = self.train_model(
            dataset_yaml=str(dataset_result["yaml_path"]),
            model_weights=model_weights,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=train_device,
            workers=workers,
            run_name=run_name,
            exist_ok=exist_ok,
            auto_load_best=auto_load_best,
        )
        return {
            "success": bool(train_result.get("success")),
            "stage": "done",
            "dataset_result": dataset_result,
            "train_result": train_result,
        }

    # -----------------------------
    # Inference methods
    # -----------------------------
    def load_model(self, model_path: str) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError(
                "ultralytics is required for model inference. Install with: pip install ultralytics"
            ) from e

        p = Path(model_path)
        if not p.exists():
            raise FileNotFoundError(f"model file not found: {model_path}")

        self.model_path = model_path
        self.model = YOLO(str(p))

    def infer(self, image: str) -> List[Dict[str, Any]]:
        if self.model is None:
            raise RuntimeError("No inference model loaded. Call load_model() or set model_path in __init__.")

        results = self.model(
            source=image,
            conf=self.conf,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []
        if not results:
            return detections

        r = results[0]
        names = getattr(r, "names", {}) or {}
        boxes = getattr(r, "boxes", None)
        if boxes is None:
            return detections

        xyxy = boxes.xyxy.cpu().tolist() if hasattr(boxes.xyxy, "cpu") else boxes.xyxy.tolist()
        confs = boxes.conf.cpu().tolist() if hasattr(boxes.conf, "cpu") else boxes.conf.tolist()
        clss = boxes.cls.cpu().tolist() if hasattr(boxes.cls, "cpu") else boxes.cls.tolist()

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]
            cls_idx = int(clss[i])
            class_name = str(names.get(cls_idx, cls_idx))
            conf = float(confs[i])
            detections.append(
                {
                    "class_idx": cls_idx,
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox": {
                        "x1": int(x1),
                        "y1": int(y1),
                        "x2": int(x2),
                        "y2": int(y2),
                    },
                    "center": {
                        "x": int((x1 + x2) / 2),
                        "y": int((y1 + y2) / 2),
                    },
                }
            )
        return detections

    def find_target(self, image: str, target_labels: Sequence[str]) -> Optional[Dict[str, Any]]:
        label_set = {self._normalize_label(x) for x in target_labels if x}
        if not label_set:
            return None

        best: Optional[Dict[str, Any]] = None
        for det in self.infer(image):
            det_label = self._normalize_label(str(det["class_name"]))
            if det_label in label_set:
                if best is None or det["confidence"] > best["confidence"]:
                    best = det
        return best

    @staticmethod
    def _normalize_label(label: str) -> str:
        normalized = label.lower().strip()
        normalized = normalized.replace("-", "_").replace(" ", "_")
        for suffix in ("_icon", "_button", "_btn", "_panel", "_page"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        return normalized
