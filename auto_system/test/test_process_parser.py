import argparse
import json
import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "auto_system", "auto_test"))

from process_parser import ProcessParser


EXAMPLE_XML_PATH = os.path.join(
    PROJECT_ROOT, "auto_system", "xml", "unified_test_flow_example.xml"
)


def parse_example_xml() -> dict:
    parser = ProcessParser()
    return parser.parse_xml(EXAMPLE_XML_PATH)


def test_parse_single_flow_xml() -> None:
    result = parse_example_xml()

    assert result["version"] == "1.0"
    assert len(result["image_resources"]) == 4
    assert len(result["test_cases"]) == 1

    test_case = result["test_cases"][0]
    assert test_case["id"] == "TC_PARSE_001"
    assert len(test_case["steps"]) == 5

    step_coordinate_swipe = test_case["steps"][1]
    loop_step_1 = test_case["steps"][2]
    loop_step_2 = test_case["steps"][3]
    step_back_home = test_case["steps"][4]

    assert loop_step_1["id"] == "3.1"
    assert loop_step_2["id"] == "3.2"

    action_types = []
    assert_types = []
    for step in test_case["steps"]:
        for item in step["actions"]:
            if item["category"] == "action":
                action_types.append(item["type"])
            elif item["category"] == "assert":
                assert_types.append(item["type"])

    assert "click_image" in action_types
    assert "click_coordinate" in action_types
    assert "wait" in action_types
    assert "swipe" in action_types
    assert "press_key" in action_types
    assert "verify_image" in assert_types
    assert "verify_text" in assert_types
    assert "verify_image_present" in assert_types
    assert "verify_page" in assert_types

    assert step_coordinate_swipe["actions"][2]["type"] == "swipe"
    assert step_coordinate_swipe["actions"][2]["params"] == {
        "startX": 300,
        "startY": 420,
        "endX": 700,
        "endY": 420,
        "duration": 600,
    }
    assert loop_step_1["actions"][2]["params"]["timeout"] == 2000
    assert step_back_home["actions"][2]["type"] == "verify_image"
    assert step_back_home["actions"][3]["type"] == "verify_page"


def print_summary(result: dict) -> None:
    print(f"Flow: {result['name']} v{result['version']}")
    print(f"Image resources: {len(result['image_resources'])}")
    for image_id, image in result["image_resources"].items():
        print(f"  - {image_id}: {image['path']} ({image['description']})")

    print(f"Test cases: {len(result['test_cases'])}")
    for case in result["test_cases"]:
        print(f"- {case['id']} {case['name']}")
        print(f"  Description: {case['description']}")
        print(f"  Steps: {len(case['steps'])}")
        for step in case["steps"]:
            print(f"    * Step {step['id']} {step['name']}")
            for action in step["actions"]:
                print(f"      - [{action['category']}] {action['type']} {action['params']}")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Test and inspect XML parse result")
    arg_parser.add_argument(
        "--json",
        action="store_true",
        help="Print full parsed result as JSON",
    )
    args = arg_parser.parse_args()

    test_parse_single_flow_xml()
    parsed = parse_example_xml()

    print("test_parse_single_flow_xml passed")
    if args.json:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print_summary(parsed)
