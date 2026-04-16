import os
import sys
import tempfile
from pathlib import Path


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "auto_system", "auto_test"))

from process_controller import ProcessController


EXAMPLE_XML_PATH = os.path.join(
    PROJECT_ROOT, "auto_system", "xml", "unified_test_flow_example.xml"
)


def test_process_controller_run_example() -> None:
    controller = ProcessController(simulate=True, stop_on_failure=True)
    result = controller.run(EXAMPLE_XML_PATH)

    assert result["success"] is True
    assert result["flow_name"] == "Parser Demo Flow"
    assert result["summary"]["total_cases"] == 1
    assert result["summary"]["total_steps"] >= 5
    assert result["summary"]["total_operations"] >= 1


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
    try:
        stop_controller = ProcessController(simulate=True, stop_on_failure=True)
        stop_result = stop_controller.run(xml_path)
        assert stop_result["success"] is False
        case_result = stop_result["test_case_results"][0]
        assert len(case_result["steps"]) == 1

        cont_controller = ProcessController(simulate=True, stop_on_failure=False)
        cont_result = cont_controller.run(xml_path)
        assert cont_result["success"] is False
        case_result_2 = cont_result["test_case_results"][0]
        assert len(case_result_2["steps"]) == 2
    finally:
        if os.path.exists(xml_path):
            os.remove(xml_path)


if __name__ == "__main__":
    test_process_controller_run_example()
    test_process_controller_failure_strategy()
    print("test_process_controller passed")
