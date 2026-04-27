import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "auto_system", "auto_test"))

from process_controller import ProcessController


EXAMPLE_XML_PATH = os.path.join(
    PROJECT_ROOT, "auto_system", "xml", "unified_test_flow_example.xml"
)

_MINI_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfeA\x8d\x89\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
)


class _FakeModelController:
    def infer(self, image: str) -> List[Dict[str, Any]]:
        # Use full-screen page anchors to make region-based matching deterministic in tests.
        return [
            {
                "class_name": "home",
                "confidence": 0.99,
                "bbox": {"x1": 0, "y1": 0, "x2": 1000, "y2": 600},
                "center": {"x": 500, "y": 300},
            },
            {
                "class_name": "ac_panel",
                "confidence": 0.95,
                "bbox": {"x1": 0, "y1": 0, "x2": 1000, "y2": 600},
                "center": {"x": 500, "y": 300},
            },
            {
                "class_name": "ac_icon",
                "confidence": 0.90,
                "bbox": {"x1": 180, "y1": 220, "x2": 240, "y2": 280},
                "center": {"x": 210, "y": 250},
            },
            {
                "class_name": "temp_up",
                "confidence": 0.92,
                "bbox": {"x1": 380, "y1": 320, "x2": 460, "y2": 400},
                "center": {"x": 420, "y": 360},
            },
        ]


def _mock_detection_inputs(controller: ProcessController) -> str:
    fd, path = tempfile.mkstemp(prefix="mock_screen_", suffix=".png")
    os.close(fd)
    Path(path).write_bytes(_MINI_PNG)
    controller.executor.set_model_controller(_FakeModelController())
    controller.executor._capture_for_detection = lambda: Path(path)  # type: ignore[attr-defined]
    return path


def test_process_controller_run_example() -> None:
    controller = ProcessController(simulate=True, stop_on_failure=True)
    temp_screen = _mock_detection_inputs(controller)
    result = controller.run(EXAMPLE_XML_PATH)
    try:
        assert result["success"] is True
        assert result["flow_name"] == "Parser Demo Flow"
        assert result["summary"]["total_cases"] == 1
        assert result["summary"]["total_steps"] >= 5
        assert result["summary"]["total_operations"] >= 1
    finally:
        if os.path.exists(temp_screen):
            os.remove(temp_screen)


def _write_temp_fail_xml() -> str:
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<CarTestFlow name="Fail Strategy Flow" version="1.0">
  <ImageResources>
    <Image id="home_icon" path="./images/home.png" description="Home icon" />
  </ImageResources>
  <TestCase id="TC_FAIL_001" name="Failure behavior">
    <Description>One bad step and one good step.</Description>
    <Steps>
      <Step id="1" name="Bad step">
        <Action type="unknown_action" />
      </Step>
      <Step id="2" name="Good step">
        <Action type="wait" duration="1" />
      </Step>
    </Steps>
  </TestCase>
</CarTestFlow>
"""
    fd, path = tempfile.mkstemp(prefix="test_fail_", suffix=".xml")
    os.close(fd)
    Path(path).write_text(xml_content, encoding="utf-8")
    return path


def test_process_controller_failure_strategy() -> None:
    xml_path = _write_temp_fail_xml()
    temp_screen_paths: List[str] = []
    try:
        stop_controller = ProcessController(simulate=True, stop_on_failure=True)
        temp_screen_paths.append(_mock_detection_inputs(stop_controller))
        stop_result = stop_controller.run(xml_path)
        assert stop_result["success"] is False
        case_result = stop_result["test_case_results"][0]
        assert len(case_result["steps"]) == 1

        cont_controller = ProcessController(simulate=True, stop_on_failure=False)
        temp_screen_paths.append(_mock_detection_inputs(cont_controller))
        cont_result = cont_controller.run(xml_path)
        assert cont_result["success"] is False
        case_result_2 = cont_result["test_case_results"][0]
        assert len(case_result_2["steps"]) == 2
    finally:
        if os.path.exists(xml_path):
            os.remove(xml_path)
        for p in temp_screen_paths:
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    test_process_controller_run_example()
    test_process_controller_failure_strategy()
    print("test_process_controller passed")
