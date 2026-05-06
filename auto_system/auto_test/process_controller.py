import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from adb_controller import AdbController
from model_controller import ModelController
from process_parser import ProcessParser


class ProcessController:
    """
    Coordinate end-to-end flow:
    XML input -> parse -> operation execution(simulate/adb) -> result output.
    """

    def __init__(
        self,
        simulate: bool = True,
        device_serial: Optional[str] = None,
        stop_on_failure: bool = True,
        model_path: Optional[str] = None,
        screen_source: str = "adb",
        model_conf: float = 0.25,
        model_iou: float = 0.7,
        model_device: str = "cpu",
    ) -> None:
        self.simulate = simulate
        self.device_serial = device_serial
        self.stop_on_failure = stop_on_failure
        self.parser = ProcessParser()
        self.executor = AdbController(device_serial=device_serial, simulate=simulate)
        self.executor.set_screen_source(screen_source)
        self.model_path = model_path
        self.model_controller: Optional[ModelController] = None
        if model_path:
            self.model_controller = ModelController(
                model_path=model_path,
                conf=model_conf,
                iou=model_iou,
                device=model_device,
            )
            self.executor.set_model_controller(self.model_controller)
            if simulate and screen_source == "adb":
                print(
                    "[WARN] model_path is set, but simulate+adb cannot capture real device screen. "
                    "Use --screen_source desktop, or enable --real_adb."
                )

    def run(self, xml_path: str) -> Dict[str, Any]:
        started_at = time.time()
        flow = self.parser.parse_xml(xml_path)
        self.executor.set_image_resources(
            flow.get("image_resources", {}),
            base_dir=str(Path(xml_path).resolve().parent),
        )

        result: Dict[str, Any] = {
            "success": True,
            "simulate": self.simulate,
            "xml_path": xml_path,
            "screen_source": self.executor.screen_source,
            "model_path": self.model_path or "",
            "flow_name": flow.get("name", ""),
            "flow_version": flow.get("version", ""),
            "image_resources_count": len(flow.get("image_resources", {})),
            "test_case_results": [],
            "summary": {},
        }

        total_cases = 0
        passed_cases = 0
        failed_cases = 0
        total_steps = 0
        passed_steps = 0
        failed_steps = 0
        total_ops = 0
        passed_ops = 0
        failed_ops = 0

        for case in flow.get("test_cases", []):
            total_cases += 1
            case_result = self._run_test_case(case)
            result["test_case_results"].append(case_result)

            total_steps += case_result["total_steps"]
            passed_steps += case_result["passed_steps"]
            failed_steps += case_result["failed_steps"]
            total_ops += case_result["total_operations"]
            passed_ops += case_result["passed_operations"]
            failed_ops += case_result["failed_operations"]

            if case_result["success"]:
                passed_cases += 1
            else:
                failed_cases += 1
                result["success"] = False
                if self.stop_on_failure:
                    break

        duration_ms = int((time.time() - started_at) * 1000)
        result["summary"] = {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "total_operations": total_ops,
            "passed_operations": passed_ops,
            "failed_operations": failed_ops,
            "duration_ms": duration_ms,
        }
        return result

    def _run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        case_started = time.time()
        steps = test_case.get("steps", [])

        case_result: Dict[str, Any] = {
            "id": test_case.get("id", ""),
            "name": test_case.get("name", ""),
            "description": test_case.get("description", ""),
            "success": True,
            "steps": [],
            "total_steps": len(steps),
            "passed_steps": 0,
            "failed_steps": 0,
            "total_operations": 0,
            "passed_operations": 0,
            "failed_operations": 0,
            "duration_ms": 0,
        }

        print(f"[CASE] {case_result['id']} {case_result['name']}")
        for step in steps:
            step_result = self._run_step(step)
            case_result["steps"].append(step_result)
            case_result["total_operations"] += step_result["total_operations"]
            case_result["passed_operations"] += step_result["passed_operations"]
            case_result["failed_operations"] += step_result["failed_operations"]

            if step_result["success"]:
                case_result["passed_steps"] += 1
            else:
                case_result["failed_steps"] += 1
                case_result["success"] = False
                if self.stop_on_failure:
                    break

        case_result["duration_ms"] = int((time.time() - case_started) * 1000)
        return case_result

    def _run_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        step_started = time.time()
        operations = step.get("actions", [])

        step_result: Dict[str, Any] = {
            "id": step.get("id", ""),
            "name": step.get("name", ""),
            "success": True,
            "operations": [],
            "total_operations": len(operations),
            "passed_operations": 0,
            "failed_operations": 0,
            "duration_ms": 0,
        }

        print(f"[STEP] {step_result['id']} {step_result['name']}")
        for op in operations:
            ok = self.executor.execute_operation(op)
            op_record = {
                "category": op.get("category", ""),
                "type": op.get("type", ""),
                "params": op.get("params", {}),
                "success": bool(ok),
            }
            step_result["operations"].append(op_record)
            if ok:
                step_result["passed_operations"] += 1
            else:
                step_result["failed_operations"] += 1
                step_result["success"] = False
                if self.stop_on_failure:
                    break

        step_result["duration_ms"] = int((time.time() - step_started) * 1000)
        return step_result


def _default_xml_path() -> str:
    script_dir = Path(__file__).parent
    auto_system_dir = script_dir.parent
    candidate_abs = auto_system_dir / "xml" / "unified_test_flow_example.xml"
    return os.path.relpath(candidate_abs, Path.cwd())


def print_run_summary(run_result: Dict[str, Any]) -> None:
    summary = run_result.get("summary", {})
    print("\n=== Run Summary ===")
    print(f"Success: {run_result.get('success')}")
    print(f"Flow: {run_result.get('flow_name')} v{run_result.get('flow_version')}")
    print(f"Screen source: {run_result.get('screen_source', '')}")
    if run_result.get("model_path"):
        print(f"Model: {run_result.get('model_path')}")
    else:
        print("Model: (not set)")
    print(
        f"Cases: {summary.get('passed_cases', 0)}/{summary.get('total_cases', 0)} passed, "
        f"failed={summary.get('failed_cases', 0)}"
    )
    print(
        f"Steps: {summary.get('passed_steps', 0)}/{summary.get('total_steps', 0)} passed, "
        f"failed={summary.get('failed_steps', 0)}"
    )
    print(
        f"Operations: {summary.get('passed_operations', 0)}/{summary.get('total_operations', 0)} passed, "
        f"failed={summary.get('failed_operations', 0)}"
    )
    print(f"Duration: {summary.get('duration_ms', 0)} ms")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Run XML car-screen test flow: parse + execute + report"
    )
    arg_parser.add_argument(
        "--xml",
        default=_default_xml_path(),
        help="Path to single-flow XML script",
    )
    arg_parser.add_argument(
        "--real_adb",
        action="store_true",
        help="Use real adb operations (default is simulate mode)",
    )
    arg_parser.add_argument(
        "--model_path",
        default=None,
        help="Path to trained YOLO model (pt). If set, image click/assert use model detection.",
    )
    arg_parser.add_argument(
        "--screen_source",
        default="adb",
        choices=["adb", "desktop"],
        help="Screen capture source for model detection: adb or desktop",
    )
    arg_parser.add_argument("--model_conf", type=float, default=0.25)
    arg_parser.add_argument("--model_iou", type=float, default=0.7)
    arg_parser.add_argument("--model_device", default="cpu")
    arg_parser.add_argument(
        "--device_serial",
        default=None,
        help="ADB device serial (optional)",
    )
    arg_parser.add_argument(
        "--continue_on_failure",
        action="store_true",
        help="Continue next operations/cases even if one fails",
    )
    arg_parser.add_argument(
        "--output_json",
        default=None,
        help="Optional output JSON result path",
    )
    args = arg_parser.parse_args()

    controller = ProcessController(
        simulate=not args.real_adb,
        device_serial=args.device_serial,
        stop_on_failure=not args.continue_on_failure,
        model_path=args.model_path,
        screen_source=args.screen_source,
        model_conf=args.model_conf,
        model_iou=args.model_iou,
        model_device=args.model_device,
    )
    run_result = controller.run(args.xml)
    print_run_summary(run_result)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(run_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Result JSON saved to: {output_path}")
