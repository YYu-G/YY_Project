import argparse
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

from yolo_dataset_builder import build_yolo_dataset, collect_image_files


def _detect_auto_system_root() -> Path:
    # Always use absolute path to avoid Ultralytics treating project as relative
    # and auto-prepending runs/detect.
    return Path(__file__).resolve().parent.parent


class ModelTrainer:
    """
    Orchestrator for dataset generation:
    raw images -> GUI annotation -> YOLO dataset export.
    """

    def __init__(self, dataset_name: str = "custom_dataset", datasets_root: Optional[str] = None):
        self.dataset_name = dataset_name
        self.auto_system_root = _detect_auto_system_root().resolve()
        self.datasets_root = (Path(datasets_root).resolve() if datasets_root else (self.auto_system_root / "datasets"))
        self.dataset_dir = self.datasets_root / dataset_name
        self.models_root = (self.auto_system_root / "yolo" / "runs").resolve()
        self.models_root.mkdir(parents=True, exist_ok=True)

    def create_dataset_with_annotation(
        self,
        raw_image_dir: str,
        class_names: Optional[List[str]] = None,
        classes_file: Optional[str] = None,
        train_ratio: float = 0.8,
        val_ratio: float = 0.2,
        test_ratio: float = 0.0,
        seed: int = 42,
        skip_unlabeled: bool = False,
        min_train_samples: int = 30,
        rare_class_names: Optional[List[str]] = None,
        rare_multiplier: int = 3,
        force_val_coverage: bool = True,
    ) -> Dict:
        if class_names is None:
            class_names = []
        if classes_file:
            class_names = load_class_names_from_file(classes_file)

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
                print("Save dataset triggered by user. Stop annotation and build dataset.")
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

        if not class_names:
            return {
                "success": False,
                "cancelled": False,
                "message": "No classes created. Press n in the annotation window to add at least one class.",
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
            min_train_samples=min_train_samples,
            rare_class_names=rare_class_names,
            rare_multiplier=rare_multiplier,
            force_val_coverage=force_val_coverage,
        )

        return {
            "success": True,
            "cancelled": False,
            "dataset_dir": export_result["dataset_dir"],
            "yaml_path": export_result["yaml_path"],
            "counts": export_result["counts"],
            "class_distribution": export_result.get("class_distribution", {}),
            "split_stats": export_result.get("split_stats", {}),
            "oversample_stats": export_result.get("oversample_stats", {}),
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
            from ultralytics.engine.trainer import BaseTrainer
        except ImportError as e:
            raise ImportError(
                "ultralytics is required for training. Install with: pip install ultralytics"
            ) from e

        self._install_ultralytics_save_retry(BaseTrainer)

        weights_path = self._resolve_weights(model_weights)
        model = YOLO(weights_path)

        run_name_unique = self._next_unique_name(self.models_root, run_name)
        train_result = model.train(
            data=str(dataset_yaml_for_train),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            workers=workers,
            # Keep run outputs under auto_system/yolo/runs
            project=str(self.models_root),
            name=run_name_unique,
            exist_ok=exist_ok,

            mosaic=0.0,     # 关闭！小数据集必关
            mixup=0.0,      # 关闭！
            
            hsv_h=0.0,
            hsv_s=0.05,
            hsv_v=0.05,
            degrees=0.0,
            translate=0.05,
            scale=0.05,
            fliplr=0.0,
            flipud=0.0,

            box=6.0,    # 定位稳定
            cls=2.5,    # 分类更强 → 稀有类别置信度直接拉高
            dfl=1.5,

            # 学习率慢 → 训练更稳定
            lr0=0.0005,
            lrf=0.005,
            
            val=True
        )

        save_dir = Path(getattr(train_result, "save_dir", self.models_root / run_name_unique))
        if not save_dir.exists():
            fallback_save_dir = self.models_root / run_name_unique
            if fallback_save_dir.exists():
                save_dir = fallback_save_dir
        best_model = save_dir / "weights" / "best.pt"
        last_model = save_dir / "weights" / "last.pt"
        # Fallback names used by our trainer patch for environments where
        # writing to last.pt/best.pt fails with Windows Errno 22.
        alt_best_model = save_dir / "weights" / "_best_ckpt.pt"
        alt_last_model = save_dir / "weights" / "_last_ckpt.pt"
        if not best_model.exists() and alt_best_model.exists():
            best_model = alt_best_model
        if not last_model.exists() and alt_last_model.exists():
            last_model = alt_last_model
        result: Dict[str, Any] = {
            "success": True,
            "dataset_yaml": str(dataset_yaml_for_train),
            "weights": str(weights_path),
            "result_dir": str(save_dir),
            "best_model": str(best_model),
            "last_model": str(last_model),
            "fixed_model_dir": str(save_dir),
            "fixed_best_model": str(best_model),
            "fixed_last_model": str(last_model),
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

    @staticmethod
    def _install_ultralytics_save_retry(base_trainer_cls: Any) -> None:
        """
        Keep training behavior unchanged, only add retry for transient Windows
        write error when Ultralytics saves last.pt/best.pt.
        """
        if getattr(base_trainer_cls, "_auto_system_save_retry_installed", False):
            return

        original_save_model = base_trainer_cls.save_model

        def save_model_with_retry(trainer_self, *args, **kwargs):
            # One-time checkpoint target remap: keep behavior the same while
            # avoiding problematic filename in some Windows environments.
            if not getattr(trainer_self, "_auto_system_ckpt_remap_done", False):
                try:
                    wdir = trainer_self.wdir
                    trainer_self.last = wdir / "_last_ckpt.pt"
                    trainer_self.best = wdir / "_best_ckpt.pt"
                except Exception:
                    pass
                trainer_self._auto_system_ckpt_remap_done = True

            last_err: Optional[OSError] = None
            for i in range(3):
                try:
                    return original_save_model(trainer_self, *args, **kwargs)
                except OSError as e:
                    path_text = str(e)
                    is_checkpoint_write = (
                        ("last.pt" in path_text)
                        or ("best.pt" in path_text)
                        or ("_last_ckpt.pt" in path_text)
                        or ("_best_ckpt.pt" in path_text)
                    )
                    if e.errno == 22 and is_checkpoint_write:
                        try:
                            trainer_self.wdir.mkdir(parents=True, exist_ok=True)
                        except Exception:
                            pass
                        time.sleep(0.25 * (i + 1))
                        last_err = e
                        continue
                    raise
            if last_err is not None:
                raise last_err

        base_trainer_cls.save_model = save_model_with_retry
        base_trainer_cls._auto_system_save_retry_installed = True

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
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--val_ratio", type=float, default=0.2)
    parser.add_argument("--test_ratio", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min_train_samples", type=int, default=30)
    parser.add_argument(
        "--rare_classes",
        default="",
        help="Comma-separated class names to over-sample in train split",
    )
    parser.add_argument("--rare_multiplier", type=int, default=3)
    parser.add_argument(
        "--no_force_val_coverage",
        action="store_true",
        help="Disable forced class coverage in val split",
    )
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
        min_train_samples=args.min_train_samples,
        rare_class_names=[x.strip() for x in args.rare_classes.split(",") if x.strip()],
        rare_multiplier=args.rare_multiplier,
        force_val_coverage=not args.no_force_val_coverage,
    )
    print(result)
