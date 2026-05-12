import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:
    yaml = None

import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def collect_image_files(raw_image_dir: str) -> List[Path]:
    root = Path(raw_image_dir)
    if not root.exists():
        raise FileNotFoundError(f"Raw image directory not found: {raw_image_dir}")

    images = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    images.sort()
    return images


def _expand_samples_to_at_least(samples: List[Dict], min_count: int = 30) -> List[Dict]:
    """
    扩充样本，直到总数 >= min_count
    """
    expanded = samples.copy()
    while len(expanded) < min_count:
        # 循环复制原样本，直到够数
        for s in samples:
            expanded.append(s.copy())
            if len(expanded) >= min_count:
                break
    return expanded


def _split_samples(
    samples: List[Dict],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    ratio_sum = train_ratio + val_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)

    n = len(shuffled)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]


def _ensure_dataset_dirs(dataset_dir: Path):
    for split in ("train", "val", "test"):
        (dataset_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_dir / "labels" / split).mkdir(parents=True, exist_ok=True)


def _write_yolo_label(label_path: Path, image_path: Path, annotations: List[Dict]):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")
    h, w = image.shape[:2]

    lines = []
    for ann in annotations:
        x1, y1, x2, y2 = ann["bbox"]
        cx = ((x1 + x2) / 2) / w
        cy = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        class_idx = ann["class_idx"]
        lines.append(f"{class_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

    label_path.write_text("\n".join(lines), encoding="utf-8")


def build_yolo_dataset(
    dataset_dir: str,
    samples: List[Dict],
    class_names: List[str],
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42,
    min_total_samples: int = 30,  # 最少 30 张
) -> Dict:
    try:
        dataset_path = Path(dataset_dir)
        _ensure_dataset_dirs(dataset_path)

        origin_total = len(samples)
        # ============== 核心修改 ==============
        samples = _expand_samples_to_at_least(samples, min_total_samples)
        expanded_total = len(samples)

        # 划分训练集/验证集/测试集
        train_samples, val_samples, test_samples = _split_samples(
            samples, train_ratio, val_ratio, test_ratio, seed
        )

        split_map = {
            "train": train_samples,
            "val": val_samples,
            "test": test_samples
        }

        # 复制图片 + 生成标签
        for split, split_samples in split_map.items():
            for idx, sample in enumerate(split_samples):
                src_img = Path(sample["image_path"])
                anns = sample["annotations"]

                new_name = f"{src_img.stem}_dup{idx}{src_img.suffix}"
                dst_img = dataset_path / "images" / split / new_name
                dst_lbl = dataset_path / "labels" / split / f"{src_img.stem}_dup{idx}.txt"

                shutil.copy2(src_img, dst_img)
                _write_yolo_label(dst_lbl, src_img, anns)

        # 生成 dataset.yaml
        yaml_path = dataset_path / "dataset.yaml"
        yaml_data = {
            "train": "./images/train",
            "val": "./images/val",
            "test": "./images/test",
            "nc": len(class_names),
            "names": class_names,
        }

        with open(yaml_path, "w", encoding="utf-8") as f:
            if yaml:
                yaml.safe_dump(yaml_data, f, sort_keys=False, allow_unicode=True)
            else:
                f.write("train: ./images/train\n")
                f.write("val: ./images/val\n")
                f.write("test: ./images/test\n")
                f.write(f"nc: {len(class_names)}\n")
                f.write("names:\n")
                for i, name in enumerate(class_names):
                    f.write(f"  {i}: {name}\n")

        return {
            "success": True,
            "dataset_dir": str(dataset_path),
            "yaml_path": str(yaml_path),
            "origin_total": origin_total,
            "expanded_total": expanded_total,
            "counts": {
                "train": len(train_samples),
                "val": len(val_samples),
                "test": len(test_samples)
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }