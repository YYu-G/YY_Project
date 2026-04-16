import os
import sys
from pathlib import Path


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "auto_system", "auto_test"))

from model_controller import ModelController


class FakeTrainer:
    def __init__(self):
        self.called = {}

    def create_dataset_with_annotation(self, **kwargs):
        self.called["create_dataset_with_annotation"] = kwargs
        return {
            "success": True,
            "yaml_path": "auto_system/datasets/fake_dataset/dataset.yaml",
            "dataset_dir": "auto_system/datasets/fake_dataset",
        }

    def train_model(self, **kwargs):
        self.called["train_model"] = kwargs
        return {
            "success": True,
            "fixed_best_model": "auto_system/yolo/fake_run/best.pt",
        }


def test_model_controller_training_orchestration() -> None:
    controller = ModelController(model_path=None)
    fake = FakeTrainer()
    controller.trainer = fake

    dataset_result = controller.create_dataset_with_annotation(
        raw_image_dir="auto_system/images",
        class_names=["home", "ac"],
    )
    assert dataset_result["success"] is True
    assert fake.called["create_dataset_with_annotation"]["raw_image_dir"] == "auto_system/images"

    train_result = controller.train_model(
        dataset_yaml="auto_system/datasets/fake_dataset/dataset.yaml",
        run_name="unit_test_run",
        auto_load_best=False,
    )
    assert train_result["success"] is True
    assert fake.called["train_model"]["run_name"] == "unit_test_run"


def test_model_controller_find_target() -> None:
    controller = ModelController(model_path=None)
    controller.infer = lambda image: [
        {"class_name": "home_icon", "confidence": 0.6, "center": {"x": 10, "y": 20}},
        {"class_name": "ac_button", "confidence": 0.9, "center": {"x": 30, "y": 40}},
    ]
    target = controller.find_target("dummy.png", ["ac_icon"])
    assert target is not None
    assert target["class_name"] == "ac_button"
    assert target["center"]["x"] == 30


if __name__ == "__main__":
    test_model_controller_training_orchestration()
    test_model_controller_find_target()
    print("test_model_controller passed")
