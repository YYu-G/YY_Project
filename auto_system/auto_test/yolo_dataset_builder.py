import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

import cv2
import numpy as np

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def collect_image_files(raw_image_dir: str) -> List[Path]:
    root = Path(raw_image_dir)
    if not root.exists():
        raise FileNotFoundError(f"Raw image directory not found: {raw_image_dir}")

    images = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    images.sort()
    return images


def _sample_class_ids(sample: Dict[str, Any]) -> List[int]:
    ids = set()
    for ann in sample.get("annotations", []):
        class_idx = ann.get("class_idx")
        if isinstance(class_idx, int):
            ids.add(class_idx)
    return sorted(ids)


def _split_samples_stratified_safe(
    samples: List[Dict[str, Any]],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
    force_val_coverage: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    ratio_sum = train_ratio + val_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    if not samples:
        return [], [], [], {}

    rng = random.Random(seed)
    indexed = list(enumerate(samples))
    rng.shuffle(indexed)

    class_to_indices: Dict[int, List[int]] = defaultdict(list)
    for idx, sample in indexed:
        class_ids = _sample_class_ids(sample)
        for cid in class_ids:
            class_to_indices[cid].append(idx)

    train_set = set()
    val_set = set()
    test_set = set()

    # Rule 1: ensure each class appears in train at least once.
    for _, indices in class_to_indices.items():
        if not indices:
            continue
        train_set.add(indices[0])

    leftovers = [idx for idx, _ in indexed if idx not in train_set]
    n = len(samples)
    target_train = max(len(train_set), int(round(n * train_ratio)))
    target_val = int(round(n * val_ratio))
    target_test = n - target_train - target_val
    if target_test < 0:
        target_test = 0
        target_val = max(0, n - target_train)

    # Rule 2: val only gets classes that have >=2 instances.
    val_allowed = set()
    for cid, indices in class_to_indices.items():
        if len(indices) >= 2:
            val_allowed.update(indices)

    # Optional rule: force val to include each class that has >=2 samples,
    # while keeping train>=1 for every class.
    forced_val_classes = 0
    if force_val_coverage:
        train_counts_tmp = defaultdict(int)
        for i in train_set:
            for cid in _sample_class_ids(samples[i]):
                train_counts_tmp[cid] += 1

        class_ids = list(class_to_indices.keys())
        rng.shuffle(class_ids)
        for cid in class_ids:
            indices = class_to_indices[cid]
            if len(indices) < 2:
                continue
            if any(i in val_set for i in indices):
                continue
            moved = False
            for i in indices:
                if i in train_set and train_counts_tmp.get(cid, 0) > 1:
                    train_set.remove(i)
                    val_set.add(i)
                    for cc in _sample_class_ids(samples[i]):
                        train_counts_tmp[cc] -= 1
                    moved = True
                    break
            if not moved:
                for i in indices:
                    if i in train_set:
                        continue
                    val_set.add(i)
                    moved = True
                    break
            if moved:
                forced_val_classes += 1

    for idx in leftovers:
        if len(train_set) < target_train:
            train_set.add(idx)
            continue
        if len(val_set) < target_val and idx in val_allowed:
            val_set.add(idx)
            continue
        if len(test_set) < target_test:
            test_set.add(idx)
            continue
        if len(val_set) < target_val:
            val_set.add(idx)
        else:
            train_set.add(idx)

    # If val/test still short, fill from train extras but never violate train>=1 per class.
    def class_counts(index_set: set) -> Dict[int, int]:
        c = defaultdict(int)
        for i in index_set:
            for cid in _sample_class_ids(samples[i]):
                c[cid] += 1
        return c

    train_counts = class_counts(train_set)
    movable = []
    for i in list(train_set):
        safe = True
        for cid in _sample_class_ids(samples[i]):
            if train_counts.get(cid, 0) <= 1:
                safe = False
                break
        if safe:
            movable.append(i)
    rng.shuffle(movable)

    while len(val_set) < target_val and movable:
        i = movable.pop()
        if i in val_allowed:
            train_set.remove(i)
            val_set.add(i)
            for cid in _sample_class_ids(samples[i]):
                train_counts[cid] -= 1

    movable = [i for i in train_set if i not in val_set and i not in test_set]
    rng.shuffle(movable)
    while len(test_set) < target_test and movable:
        i = movable.pop()
        safe = True
        for cid in _sample_class_ids(samples[i]):
            if train_counts.get(cid, 0) <= 1:
                safe = False
                break
        if not safe:
            continue
        train_set.remove(i)
        test_set.add(i)
        for cid in _sample_class_ids(samples[i]):
            train_counts[cid] -= 1

    train_samples = [samples[i] for i in sorted(train_set)]
    val_samples = [samples[i] for i in sorted(val_set)]
    test_samples = [samples[i] for i in sorted(test_set)]

    stats = {
        "targets": {"train": target_train, "val": target_val, "test": target_test},
        "actual": {"train": len(train_samples), "val": len(val_samples), "test": len(test_samples)},
        "force_val_coverage": force_val_coverage,
        "forced_val_classes": forced_val_classes,
    }
    return train_samples, val_samples, test_samples, stats


def _class_counter(samples: List[Dict[str, Any]]) -> Dict[int, int]:
    counts = defaultdict(int)
    for s in samples:
        for cid in _sample_class_ids(s):
            counts[cid] += 1
    return dict(counts)


def _oversample_train(
    train_samples: List[Dict[str, Any]],
    min_train_samples: int = 30,
    rare_class_ids: Optional[List[int]] = None,
    rare_multiplier: int = 3,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not train_samples:
        return [], {"added_min_train": 0, "added_rare": 0}

    rng = random.Random(seed)
    expanded = list(train_samples)

    added_rare = 0
    if rare_class_ids:
        target_set = set(rare_class_ids)
        rare_pool = [s for s in train_samples if target_set.intersection(_sample_class_ids(s))]
        if rare_pool and rare_multiplier > 1:
            for _ in range(rare_multiplier - 1):
                shuffled = list(rare_pool)
                rng.shuffle(shuffled)
                for s in shuffled:
                    expanded.append(s)
                    added_rare += 1

    added_min_train = 0
    base_pool = list(expanded)
    while len(expanded) < min_train_samples and base_pool:
        shuffled = list(base_pool)
        rng.shuffle(shuffled)
        for s in shuffled:
            expanded.append(s)
            added_min_train += 1
            if len(expanded) >= min_train_samples:
                break

    return expanded, {"added_min_train": added_min_train, "added_rare": added_rare}


def _ensure_dataset_dirs(dataset_dir: Path) -> None:
    for split in ("train", "val", "test"):
        (dataset_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_dir / "labels" / split).mkdir(parents=True, exist_ok=True)


def _write_yolo_label(label_path: Path, image_path: Path, annotations: List[Dict[str, Any]]) -> None:
    image = _imread_unicode_safe(image_path)
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


def _imread_unicode_safe(image_path: Path):
    """
    Read image robustly on Windows for paths containing non-ASCII characters.
    """
    try:
        raw = np.fromfile(str(image_path), dtype=np.uint8)
        if raw.size == 0:
            return None
        img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return cv2.imread(str(image_path))


def _export_split(dataset_path: Path, split: str, split_samples: List[Dict[str, Any]]) -> None:
    for idx, sample in enumerate(split_samples):
        src_img = Path(sample["image_path"])
        anns = sample["annotations"]
        new_stem = f"{src_img.stem}_{split}_{idx:05d}"
        dst_img = dataset_path / "images" / split / f"{new_stem}{src_img.suffix.lower()}"
        dst_lbl = dataset_path / "labels" / split / f"{new_stem}.txt"
        shutil.copy2(src_img, dst_img)
        _write_yolo_label(dst_lbl, src_img, anns)


def build_yolo_dataset(
    dataset_dir: str,
    samples: List[Dict[str, Any]],
    class_names: List[str],
    train_ratio: float = 0.8,
    val_ratio: float = 0.2,
    test_ratio: float = 0.0,
    seed: int = 42,
    min_train_samples: int = 30,
    rare_class_names: Optional[List[str]] = None,
    rare_multiplier: int = 3,
    force_val_coverage: bool = True,
) -> Dict[str, Any]:
    dataset_path = Path(dataset_dir)
    _ensure_dataset_dirs(dataset_path)

    if not samples:
        return {"success": False, "error": "No samples for dataset export"}

    rare_class_ids: List[int] = []
    if rare_class_names:
        name_to_idx = {name: idx for idx, name in enumerate(class_names)}
        for n in rare_class_names:
            if n in name_to_idx:
                rare_class_ids.append(name_to_idx[n])

    train_samples, val_samples, test_samples, split_stats = _split_samples_stratified_safe(
        samples=samples,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
        force_val_coverage=force_val_coverage,
    )
    train_samples, oversample_stats = _oversample_train(
        train_samples=train_samples,
        min_train_samples=min_train_samples,
        rare_class_ids=rare_class_ids,
        rare_multiplier=rare_multiplier,
        seed=seed,
    )

    _export_split(dataset_path, "train", train_samples)
    _export_split(dataset_path, "val", val_samples)
    _export_split(dataset_path, "test", test_samples)

    yaml_path = dataset_path / "dataset.yaml"
    yaml_data = {
        "path": ".",
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
            f.write("path: .\n")
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
        "counts": {
            "total_input": len(samples),
            "train": len(train_samples),
            "val": len(val_samples),
            "test": len(test_samples),
        },
        "class_distribution": {
            "train": _class_counter(train_samples),
            "val": _class_counter(val_samples),
            "test": _class_counter(test_samples),
        },
        "split_stats": split_stats,
        "oversample_stats": oversample_stats,
    }
