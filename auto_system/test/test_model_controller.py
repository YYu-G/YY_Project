import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict


SCRIPT_DIR = Path(__file__).resolve().parent
AUTO_SYSTEM_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AUTO_SYSTEM_DIR.parent
AUTO_TEST_DIR = AUTO_SYSTEM_DIR / "auto_test"
sys.path.insert(0, str(AUTO_TEST_DIR))

from model_controller import ModelController


def _to_rel(path: Path) -> str:
    return os.path.relpath(path.resolve(), Path.cwd())


def print_pipeline_config(args: argparse.Namespace) -> None:
    print("=== ModelController Pipeline Config ===")
    print(f"raw_dir: {args.raw_dir}")
    print(f"classes_file: {args.classes_file}")
    print(f"dataset_name: {args.dataset_name}")
    print(f"datasets_root: {args.datasets_root}")
    print(
        "train params: "
        f"weights={args.weights}, epochs={args.epochs}, imgsz={args.imgsz}, "
        f"batch={args.batch}, device={args.device}, workers={args.workers}, run_name={args.run_name}"
    )


def print_result(result: Dict) -> None:
    print("\n=== Pipeline Result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="E2E test for ModelController: raw images -> annotation dataset -> YOLO training."
    )
    parser.add_argument(
        "--raw_dir",
        default=_to_rel(AUTO_SYSTEM_DIR / "images"),
        help="Raw image directory path.",
    )
    parser.add_argument(
        "--classes_file",
        default=_to_rel(SCRIPT_DIR / "classes.txt"),
        help="Class definition file path.",
    )
    parser.add_argument("--dataset_name", default="test_model_controller_pipeline")
    parser.add_argument(
        "--datasets_root",
        default=_to_rel(AUTO_SYSTEM_DIR / "datasets"),
        help="Datasets root directory.",
    )

    parser.add_argument("--weights", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--run_name", default="result_from_model_controller_test")
    parser.add_argument("--skip_unlabeled", action="store_true")
    parser.add_argument(
        "--output_json",
        default=_to_rel(SCRIPT_DIR / "model_controller_pipeline_result.json"),
        help="Optional output JSON file path for pipeline result.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Actually run annotation UI + training. Without this flag, only do check mode.",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    classes_file = Path(args.classes_file)
    datasets_root = Path(args.datasets_root)

    print_pipeline_config(args)

    if not raw_dir.exists():
        print(f"raw_dir does not exist: {raw_dir}")
        return
    if not classes_file.exists():
        print(f"classes_file does not exist: {classes_file}")
        return

    if not args.run:
        print("\nCheck mode only. Add --run to execute full pipeline.")
        if args.output_json:
            output_path = Path(args.output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            check_result = {
                "success": False,
                "stage": "check_only",
                "message": "Check mode only. Add --run to execute full pipeline.",
                "config": {
                    "raw_dir": str(raw_dir),
                    "classes_file": str(classes_file),
                    "dataset_name": args.dataset_name,
                    "datasets_root": str(datasets_root),
                    "weights": args.weights,
                    "epochs": args.epochs,
                    "imgsz": args.imgsz,
                    "batch": args.batch,
                    "device": args.device,
                    "workers": args.workers,
                    "run_name": args.run_name,
                },
            }
            output_path.write_text(
                json.dumps(check_result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Check JSON saved to: {output_path}")
        return

    controller = ModelController(
        model_path=None,
        dataset_name=args.dataset_name,
        datasets_root=str(datasets_root),
    )

    result = controller.build_and_train(
        raw_image_dir=str(raw_dir),
        classes_file=str(classes_file),
        skip_unlabeled=args.skip_unlabeled,
        model_weights=args.weights,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        train_device=args.device,
        workers=args.workers,
        run_name=args.run_name,
        exist_ok=True,
        auto_load_best=True,
    )
    print_result(result)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nResult JSON saved to: {output_path}")


if __name__ == "__main__":
    main()
