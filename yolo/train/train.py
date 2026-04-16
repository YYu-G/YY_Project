from ultralytics import YOLO
import os
import sys

# 核心：将工作目录强制设为当前脚本（train.py）所在目录
# 解决 VS Code/PyCharm 工作目录不一致问题
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 动态获取 yolo.yaml 绝对路径（和脚本同目录）
yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolo.yaml")
# 验证文件是否存在（方便排查）
if not os.path.exists(yaml_path):
    raise FileNotFoundError(f"找不到 yolo.yaml 文件，路径：{yaml_path}")

# 加载模型
model_path = "D:/uid02310/Desktop/YY_Project/yolo/train/runs/models/result15/weights/best.pt"
model = YOLO(model_path)

# 训练模型
results = model.train(
    data=yaml_path,  # 用绝对路径
    epochs=150,
    batch=2,
    imgsz=1024,
    device="cpu",
    mosaic=1.0,
    mixup=0.2,
    hsv_h=0.05,
    hsv_s=0.3,
    perspective=0.0,
    box=10.0,
    cls=1.0,
    lr0=0.0005,
    val=True,
    save=True,
    project="../models",
    name="result",
)