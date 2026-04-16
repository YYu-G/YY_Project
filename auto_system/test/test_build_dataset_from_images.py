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
from yolo_dataset_builder import collect_image_files


def main():
    parser = argparse.ArgumentParser(
        description="Test dataset generation from auto_system/images"
    )
    parser.add_argument(
        "--classes_file",
        default=str(CURRENT_DIR / "classes.txt"),
        help="Class definition file path",
    )
    parser.add_argument(
        "--dataset_name",
        default="test_from_auto_system_images",
        help="Output dataset name under datasets/",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run GUI annotation and build dataset",
    )
    args = parser.parse_args()

    raw_dir = AUTO_SYSTEM_DIR / "images"
    print(f"Raw image dir: {raw_dir}")

    image_files = collect_image_files(str(raw_dir))
    print(f"Found images: {len(image_files)}")
    for p in image_files:
        print(f"  - {p.name}")

    if not args.run:
        print("\nCheck mode only. To run annotation and export dataset, add --run")
        return

    trainer = ModelTrainer(dataset_name=args.dataset_name, datasets_root=str(AUTO_SYSTEM_DIR / "datasets"))
    result = trainer.create_dataset_with_annotation(
        raw_image_dir=str(raw_dir),
        classes_file=args.classes_file,
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1,
        seed=42,
        skip_unlabeled=False,
    )
    print("\nResult:")
    print(result)


if __name__ == "__main__":
    main()
