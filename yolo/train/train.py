from ultralytics import YOLO
import os
import sys

# 加载模型
model_path = "D:/uid02310/Desktop/YY_Project/yolo/train/yolo11n.pt"
model = YOLO(model_path)

# 训练模型
results = model.train(
    data="D:/uid02310/Desktop/YY_Project/auto_system/datasets/test5_20260512_130132/dataset.yaml",  # 用绝对路径
    epochs=150,
    batch=2,
    imgsz=1024,
    device="cpu",

    mosaic=0.0,     # 关闭！小数据集必关
    mixup=0.0,      # 关闭！

    hsv_h=0.0,
    hsv_s=0.05,
    hsv_v=0.05,
    degrees=0.0,
    translate=0.05,
    scale=0.05,
    fliplr=0.0,
    flipud=0.0,

    box=6.0,    # 定位稳定
    cls=2.5,    # 分类更强 → 稀有类别置信度直接拉高
    dfl=1.5,

     # 学习率慢 → 训练更稳定
    lr0=0.0005,
    lrf=0.005,

    # 其他
    val=True,
    save=True,
    project="../models",
    name="result_final_v2",  # 最终模型
)