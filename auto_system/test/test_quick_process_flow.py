import argparse
import json
import sys
from pathlib import Path


def _prepare_import_path() -> None:
    this_file = Path(__file__).resolve()
    auto_system_dir = this_file.parent.parent
    auto_test_dir = auto_system_dir / "auto_test"
    if str(auto_test_dir) not in sys.path:
        sys.path.insert(0, str(auto_test_dir))


def _default_xml_path() -> Path:
    return Path(__file__).resolve().parent / "quick_flow_smoke.xml"


def _default_model_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "yolo"
        / "actual2.1_20260513_172715"
        / "best.pt"
    )


def print_summary(result: dict) -> None:
    summary = result.get("summary", {}) or {}
    print("\n=== Quick Flow Summary ===")
    print(f"Success: {result.get('success')}")
    print(f"Flow: {result.get('flow_name')} v{result.get('flow_version')}")
    print(f"Screen source: {result.get('screen_source')}")
    print(f"Model path: {result.get('model_path')}")
    print(
        f"Cases: {summary.get('passed_cases', 0)}/{summary.get('total_cases', 0)} "
        f"(failed={summary.get('failed_cases', 0)})"
    )
    print(
        f"Operations: {summary.get('passed_operations', 0)}/{summary.get('total_operations', 0)} "
        f"(failed={summary.get('failed_operations', 0)})"
    )
    print(f"Duration: {summary.get('duration_ms', 0)} ms")


def print_setting_diag(result: dict) -> None:
    setting_case = None
    for case in result.get("test_case_results", []) or []:
        if case.get("id") == "TC_DIAG_SETTING_001":
            setting_case = case
            break
    if setting_case is None:
        print("\n[DIAG] setting case not found.")
        return

    total = int(setting_case.get("total_steps", 0))
    passed = int(setting_case.get("passed_steps", 0))
    failed = int(setting_case.get("failed_steps", 0))
    rate = (passed / total * 100.0) if total > 0 else 0.0
    print("\n=== Setting Diagnostic ===")
    print(f"Passed: {passed}/{total} ({rate:.1f}%)")
    print(f"Failed: {failed}/{total}")


def main() -> int:
    _prepare_import_path()
    from process_controller import ProcessController

    parser = argparse.ArgumentParser(
        description="Quick process-flow smoke test with desktop capture + trained model."
    )
    parser.add_argument("--run", action="store_true", help="Actually run the test")
    parser.add_argument("--xml", default=str(_default_xml_path()))
    parser.add_argument("--model", default=str(_default_model_path()))
    parser.add_argument("--real_adb", action="store_true", help="Use real adb tap/swipe/key actions")
    parser.add_argument(
        "--screen_source",
        default="adb",
        choices=["adb", "desktop"],
        help="Screen capture source for model detection",
    )
    parser.add_argument("--device_serial", default=None)
    parser.add_argument("--continue_on_failure", action="store_true")
    parser.add_argument("--output_json", default="")
    args = parser.parse_args()

    if not args.run:
        print("Dry run mode. Use --run to execute.")
        print(f"XML: {args.xml}")
        print(f"Model: {args.model}")
        print(f"Capture source: {args.screen_source}")
        print("Example:")
        print(
            "  python auto_system/test/test_quick_process_flow.py --run "
            "--continue_on_failure"
        )
        return 0

    xml_path = Path(args.xml).resolve()
    model_path = Path(args.model).resolve()
    if not xml_path.exists():
        raise FileNotFoundError(f"XML not found: {xml_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    controller = ProcessController(
        simulate=not args.real_adb,
        device_serial=args.device_serial,
        stop_on_failure=not args.continue_on_failure,
        model_path=str(model_path),
        screen_source=args.screen_source,
        model_conf=0.2,
        model_iou=0.7,
        model_device="cpu",
    )

    result = controller.run(str(xml_path))
    print_summary(result)
    print_setting_diag(result)

    if args.output_json:
        out_path = Path(args.output_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON saved to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
