import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

from yolo_dataset_builder import build_yolo_dataset, collect_image_files


def _detect_auto_system_root() -> Path:
    auto_system_abs = Path(__file__).resolve().parent.parent
    return Path(os.path.relpath(auto_system_abs, Path.cwd()))


class ModelTrainer:
    """
    Orchestrator for dataset generation:
    raw images -> GUI annotation -> YOLO dataset export.
    """

    def __init__(self, dataset_name: str = "custom_dataset", datasets_root: Optional[str] = None):
        self.dataset_name = dataset_name
        self.auto_system_root = _detect_auto_system_root()
        self.datasets_root = Path(datasets_root) if datasets_root else (self.auto_system_root / "datasets")
        self.dataset_dir = self.datasets_root / dataset_name
        self.models_root = self.auto_system_root / "yolo" / "runs"
        self.models_root.mkdir(parents=True, exist_ok=True)
        self.fixed_models_dir = self.auto_system_root / "yolo"
        self.fixed_models_dir.mkdir(parents=True, exist_ok=True)

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
    ) -> Dict:
        if class_names is None:
            class_names = []
        if classes_file:
            class_names = load_class_names_from_file(classes_file)
        if not class_names:
            raise ValueError("class_names is empty, provide class_names or classes_file")

        image_files = collect_image_files(raw_image_dir)
        if not image_files:
            raise ValueError(f"No images found in: {raw_image_dir}")

        samples = []
        total = len(image_files)
        print(f"Found {total} images. Start annotation...")

        image_paths = [str(p) for p in image_files]
        annotation_store: Dict[str, List[Dict[str, Any]]] = {}
        i = 0
        while 0 <= i < total:
            image_path = image_files[i]
            print(f"[{i + 1}/{total}] Annotating: {image_path.name}")
            from annotation_ui import AnnotationTool

            tool = AnnotationTool(
                str(image_path),
                class_names,
                image_paths=image_paths,
                current_image_idx=i,
                initial_annotations=annotation_store.get(str(image_path), []),
            )
            annotations = tool.run()

            if annotations is None:
                return {
                    "success": False,
                    "cancelled": True,
                    "message": f"Annotation cancelled at image: {image_path.name}",
                }

            annotation_store[str(image_path)] = annotations

            if getattr(tool, "finish_session", False):
                print("Finish triggered by user (key: s). Stop annotation and build dataset.")
                break

            jump_to = tool.pending_jump_image_idx
            if jump_to is not None and 0 <= jump_to < total and jump_to != i:
                i = jump_to
            else:
                i += 1

        # Build samples after annotation session, preserving image order.
        samples = []
        for p in image_files:
            if str(p) not in annotation_store:
                continue
            anns = annotation_store.get(str(p), [])
            if skip_unlabeled and not anns:
                continue
            samples.append({"image_path": str(p), "annotations": anns})

        if not samples:
            return {
                "success": False,
                "cancelled": False,
                "message": "No samples available after annotation.",
            }

        dataset_dir = self._next_unique_dir(self.datasets_root, self.dataset_name)
        export_result = build_yolo_dataset(
            dataset_dir=str(dataset_dir),
            samples=samples,
            class_names=class_names,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )

        return {
            "success": True,
            "cancelled": False,
            "dataset_dir": export_result["dataset_dir"],
            "yaml_path": export_result["yaml_path"],
            "counts": export_result["counts"],
            "class_names": class_names,
        }

    def prepare_dataset(
        self, image_dir: str, class_names: Optional[List[str]] = None, classes_file: Optional[str] = None
    ) -> Dict:
        """
        Compatibility alias. Calls annotation-based workflow.
        """
        return self.create_dataset_with_annotation(
            raw_image_dir=image_dir,
            class_names=class_names,
            classes_file=classes_file,
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
    ) -> Dict[str, Any]:
        """
        Train YOLO model from a dataset yaml file.
        """
        dataset_yaml_path = Path(dataset_yaml)
        if not dataset_yaml_path.exists():
            raise FileNotFoundError(f"dataset yaml not found: {dataset_yaml}")
        dataset_yaml_for_train = self._prepare_dataset_yaml_for_training(dataset_yaml_path)

        # Lazy import: keep dataset-related features usable even if ultralytics
        # is unavailable in current environment.
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError(
                "ultralytics is required for training. Install with: pip install ultralytics"
            ) from e

        weights_path = self._resolve_weights(model_weights)
        model = YOLO(weights_path)

        run_name_unique = self._next_unique_name(self.fixed_models_dir, run_name)
        train_result = model.train(
            data=str(dataset_yaml_for_train),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            workers=workers,
            project=str(self.models_root),
            name=run_name_unique,
            exist_ok=exist_ok,
        )

        save_dir = Path(getattr(train_result, "save_dir", self.models_root / run_name_unique))
        best_model = save_dir / "weights" / "best.pt"
        last_model = save_dir / "weights" / "last.pt"
        fixed_dir = self.fixed_models_dir / run_name_unique
        fixed_dir.mkdir(parents=True, exist_ok=True)

        fixed_best = fixed_dir / "best.pt"
        fixed_last = fixed_dir / "last.pt"
        if best_model.exists():
            shutil.copy2(best_model, fixed_best)
        if last_model.exists():
            shutil.copy2(last_model, fixed_last)

        for aux_name in ("args.yaml", "results.csv", "results.png", "confusion_matrix.png"):
            aux_src = save_dir / aux_name
            if aux_src.exists():
                shutil.copy2(aux_src, fixed_dir / aux_name)

        result: Dict[str, Any] = {
            "success": True,
            "dataset_yaml": str(dataset_yaml_for_train),
            "weights": str(weights_path),
            "result_dir": str(save_dir),
            "best_model": str(best_model),
            "last_model": str(last_model),
            "fixed_model_dir": str(fixed_dir),
            "fixed_best_model": str(fixed_best),
            "fixed_last_model": str(fixed_last),
            "params": {
                "epochs": epochs,
                "imgsz": imgsz,
                "batch": batch,
                "device": device,
                "workers": workers,
                "run_name": run_name_unique,
            },
        }

        results_csv = save_dir / "results.csv"
        if results_csv.exists():
            result["results_csv"] = str(results_csv)
        return result

    def _prepare_dataset_yaml_for_training(self, dataset_yaml_path: Path) -> Path:
        """
        Ultralytics may resolve `path: .` against current working directory.
        Generate a runtime yaml that pins `path` to dataset yaml parent when needed.
        """
        if yaml is None:
            return dataset_yaml_path

        try:
            data = yaml.safe_load(dataset_yaml_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return dataset_yaml_path

        if not isinstance(data, dict):
            return dataset_yaml_path

        path_value = data.get("path")
        if path_value not in (".", "./"):
            return dataset_yaml_path

        patched = dict(data)
        patched["path"] = str(dataset_yaml_path.parent)
        runtime_yaml = dataset_yaml_path.parent / "_runtime_dataset.yaml"
        with open(runtime_yaml, "w", encoding="utf-8") as f:
            yaml.safe_dump(patched, f, sort_keys=False, allow_unicode=True)
        return runtime_yaml

    def _resolve_weights(self, model_weights: str) -> str:
        candidate = Path(model_weights)
        if candidate.exists():
            return str(candidate)

        common_local = Path("yolo") / "models" / model_weights
        if common_local.exists():
            return str(common_local)

        # Fall back to Ultralytics model hub name.
        return model_weights

    def _next_unique_name(self, root: Path, base_name: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate = f"{base_name}_{stamp}"
        idx = 1
        while (root / candidate).exists() or (self.models_root / candidate).exists():
            idx += 1
            candidate = f"{base_name}_{stamp}_{idx}"
        return candidate

    def _next_unique_dir(self, root: Path, base_name: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate = root / f"{base_name}_{stamp}"
        idx = 1
        while candidate.exists():
            idx += 1
            candidate = root / f"{base_name}_{stamp}_{idx}"
        return candidate


def load_class_names_from_file(classes_file: str) -> List[str]:
    path = Path(classes_file)
    if not path.exists():
        raise FileNotFoundError(f"classes file not found: {classes_file}")

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("classes file is empty")

    if "\n" in raw:
        classes = [line.strip() for line in raw.splitlines() if line.strip()]
    else:
        classes = [item.strip() for item in raw.split(",") if item.strip()]

    # De-duplicate while preserving order.
    deduped = list(dict.fromkeys(classes))
    classes = deduped
    if not classes:
        raise ValueError("no valid classes loaded from file")
    return classes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build YOLO dataset from raw images via GUI annotation."
    )
    parser.add_argument("--raw_dir", required=True, help="Directory with raw images")
    parser.add_argument(
        "--classes_file",
        required=True,
        help="Path to class definition file (one class per line, or comma-separated one line)",
    )
    parser.add_argument("--dataset_name", default="custom_dataset")
    parser.add_argument("--datasets_root", default=None)
    parser.add_argument("--train_ratio", type=float, default=0.7)
    parser.add_argument("--val_ratio", type=float, default=0.2)
    parser.add_argument("--test_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--skip_unlabeled",
        action="store_true",
        help="Skip images without annotations",
    )

    args = parser.parse_args()

    trainer = ModelTrainer(dataset_name=args.dataset_name, datasets_root=args.datasets_root)
    result = trainer.create_dataset_with_annotation(
        raw_image_dir=args.raw_dir,
        classes_file=args.classes_file,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
        skip_unlabeled=args.skip_unlabeled,
    )
    print(result)
