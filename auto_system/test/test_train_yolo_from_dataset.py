import argparse
import os
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
AUTO_SYSTEM_DIR = Path(os.path.relpath(SCRIPT_DIR.parent, Path.cwd()))
CURRENT_DIR = Path(os.path.relpath(SCRIPT_DIR, Path.cwd()))
AUTO_TEST_DIR = Path(os.path.relpath(SCRIPT_DIR.parent / "auto_test", Path.cwd()))
sys.path.insert(0, str(AUTO_TEST_DIR))

from model_trainer import ModelTrainer


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end test: annotation dataset build -> YOLO training."
    )

    # Dataset annotation/build stage
    parser.add_argument(
        "--raw_dir",
        default=str(AUTO_SYSTEM_DIR / "images"),
        help="Raw image directory for annotation",
    )
    parser.add_argument(
        "--classes_file",
        default=str(CURRENT_DIR / "classes.txt"),
        help="Class definition file path",
    )
    parser.add_argument("--dataset_name", default="test_from_auto_system_images")
    parser.add_argument(
        "--datasets_root",
        default=str(AUTO_SYSTEM_DIR / "datasets"),
        help="Datasets root directory",
    )
    parser.add_argument("--train_ratio", type=float, default=0.7)
    parser.add_argument("--val_ratio", type=float, default=0.2)
    parser.add_argument("--test_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip_unlabeled", action="store_true")

    # Training stage
    parser.add_argument("--weights", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--run_name", default="result_from_test_pipeline")

    parser.add_argument(
        "--run",
        action="store_true",
        help="Actually run annotation build and training",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    classes_file = Path(args.classes_file)
    datasets_root = Path(args.datasets_root)
    dataset_yaml = datasets_root / args.dataset_name / "dataset.yaml"

    print("=== Pipeline Config ===")
    print(f"raw_dir: {raw_dir}")
    print(f"classes_file: {classes_file}")
    print(f"datasets_root: {datasets_root}")
    print(f"dataset_name: {args.dataset_name}")
    print(f"expected_dataset_yaml: {dataset_yaml}")
    print(
        f"train params: weights={args.weights}, epochs={args.epochs}, imgsz={args.imgsz}, "
        f"batch={args.batch}, device={args.device}, workers={args.workers}, run_name={args.run_name}"
    )

    if not raw_dir.exists():
        print("raw_dir does not exist.")
        return
    if not classes_file.exists():
        print("classes_file does not exist.")
        return

    if not args.run:
        print("\nCheck mode only. Add --run to execute full pipeline.")
        return

    trainer = ModelTrainer(dataset_name=args.dataset_name, datasets_root=str(datasets_root))

    print("\n=== Step 1: Build Dataset With Annotation ===")
    build_result = trainer.create_dataset_with_annotation(
        raw_image_dir=str(raw_dir),
        classes_file=str(classes_file),
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
        skip_unlabeled=args.skip_unlabeled,
    )
    print(build_result)

    if not build_result.get("success"):
        print("\nBuild stage did not complete successfully. Stop pipeline.")
        return

    built_yaml = build_result["yaml_path"]

    print("\n=== Step 2: Train YOLO Model ===")
    train_result = trainer.train_model(
        dataset_yaml=built_yaml,
        model_weights=args.weights,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        run_name=args.run_name,
        exist_ok=True,
    )
    print(train_result)


if __name__ == "__main__":
    main()
