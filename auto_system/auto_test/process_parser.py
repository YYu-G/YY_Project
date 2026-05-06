import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


class ProcessParser:
    """Parse a single XML schema: CarTestFlow."""

    def __init__(self) -> None:
        self.test_flow: Dict[str, Any] = {}
        self.image_resources: Dict[str, Dict[str, str]] = {}
        self.test_cases: List[Dict[str, Any]] = []

    def parse_xml(self, xml_path: str) -> Dict[str, Any]:
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XML file not found: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()
        if root.tag != "CarTestFlow":
            raise ValueError(f"Unsupported root tag: {root.tag}, expected CarTestFlow")

        self.image_resources = self._parse_image_resources(root.find("ImageResources"))

        self.test_cases = []
        for test_case_elem in root.findall("TestCase"):
            self.test_cases.append(self._parse_test_case(test_case_elem))

        self.test_flow = {
            "name": root.get("name", "UnnamedFlow"),
            "version": root.get("version", "1.0"),
            "image_resources": self.image_resources,
            "test_cases": self.test_cases,
        }
        return self.test_flow

    def _parse_image_resources(self, image_resources_elem: Optional[ET.Element]) -> Dict[str, Dict[str, str]]:
        resources: Dict[str, Dict[str, str]] = {}
        if image_resources_elem is None:
            return resources

        for image_elem in image_resources_elem.findall("Image"):
            image_id = image_elem.get("id")
            if not image_id:
                continue
            resources[image_id] = {
                "id": image_id,
                "path": image_elem.get("path", ""),
                "className": image_elem.get("className", ""),
                "class_name": image_elem.get("class_name", ""),
                "modelClass": image_elem.get("modelClass", ""),
                "label": image_elem.get("label", ""),
                "aliases": image_elem.get("aliases", ""),
                "description": image_elem.get("description", ""),
            }
        return resources

    def _parse_test_case(self, test_case_elem: ET.Element) -> Dict[str, Any]:
        test_case: Dict[str, Any] = {
            "id": test_case_elem.get("id", ""),
            "name": test_case_elem.get("name", ""),
            "description": "",
            "steps": [],
        }

        desc_elem = test_case_elem.find("Description")
        if desc_elem is not None and desc_elem.text:
            test_case["description"] = desc_elem.text.strip()

        steps_elem = test_case_elem.find("Steps")
        if steps_elem is not None:
            test_case["steps"] = self._parse_steps(steps_elem, {})

        return test_case

    def _parse_steps(self, steps_elem: ET.Element, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []

        for elem in steps_elem:
            if elem.tag == "Step":
                step = self._parse_step(elem, context)
                if step:
                    steps.append(step)
            elif elem.tag == "Loop":
                steps.extend(self._parse_loop(elem, context))

        return steps

    def _parse_loop(self, loop_elem: ET.Element, parent_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        times = int(loop_elem.get("times", "1"))
        loop_steps: List[Dict[str, Any]] = []

        for i in range(1, times + 1):
            loop_context = dict(parent_context)
            loop_context["iteration"] = i

            for elem in loop_elem:
                if elem.tag == "Step":
                    step = self._parse_step(elem, loop_context)
                    if step:
                        loop_steps.append(step)

        return loop_steps

    def _parse_step(self, step_elem: ET.Element, context: Dict[str, Any]) -> Dict[str, Any]:
        step_id = self._render_template(step_elem.get("id", ""), context)
        step_name = self._render_template(step_elem.get("name", ""), context)

        step: Dict[str, Any] = {
            "id": step_id,
            "name": step_name,
            "actions": [],
        }

        for child in step_elem:
            parsed = self._parse_step_item(child, context)
            if parsed:
                step["actions"].append(parsed)

        return step

    def _parse_step_item(self, elem: ET.Element, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if elem.tag == "Action":
            item_type = elem.get("type", "").strip().lower()
            item: Dict[str, Any] = {
                "category": "action",
                "type": item_type,
                "params": self._normalize_attrs(elem.attrib, context, skip_keys={"type"}),
            }
            return item

        if elem.tag == "Assert":
            item_type = elem.get("type", "").strip().lower()
            item = {
                "category": "assert",
                "type": item_type,
                "params": self._normalize_attrs(elem.attrib, context, skip_keys={"type"}),
            }
            return item

        return None

    def _normalize_attrs(self, attrs: Dict[str, str], context: Dict[str, Any], skip_keys: set) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in attrs.items():
            if key in skip_keys:
                continue
            rendered = self._render_template(value, context)

            if key in {"x", "y", "startX", "startY", "endX", "endY", "duration", "timeout"}:
                try:
                    normalized[key] = int(rendered)
                    continue
                except ValueError:
                    pass

            if key == "region":
                parts = [p.strip() for p in rendered.split(",")]
                if len(parts) == 4 and all(p.lstrip("-").isdigit() for p in parts):
                    normalized[key] = {
                        "x": int(parts[0]),
                        "y": int(parts[1]),
                        "width": int(parts[2]),
                        "height": int(parts[3]),
                    }
                    continue

            normalized[key] = rendered

        return normalized

    def _render_template(self, text: str, context: Dict[str, Any]) -> str:
        rendered = text
        for key, value in context.items():
            rendered = rendered.replace(f"${{{key}}}", str(value))
        return rendered


if __name__ == "__main__":
    parser = ProcessParser()
    xml_file = os.path.join(
        os.path.dirname(__file__), "..", "xml", "unified_test_flow_example.xml"
    )
    result = parser.parse_xml(xml_file)
    print(f"Flow: {result['name']} v{result['version']}")
    print(f"Image resources: {len(result['image_resources'])}")
    print(f"Test cases: {len(result['test_cases'])}")
    for tc in result["test_cases"]:
        print(f"- {tc['id']} ({len(tc['steps'])} steps)")
