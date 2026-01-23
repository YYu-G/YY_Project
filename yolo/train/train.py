from ultralytics import YOLO

model = YOLO("D:/uid02310/Desktop/YY_Project/yolo/train/runs/models/result15/weights/best.pt")
#D:/uid02310/Desktop/YY_Project/yolo/train/runs/models/result15/weights/best.pt
#D:/uid02310/Desktop/YY_Project/yolo/models/icon.pt

results = model.train(
    data="yolo.yaml",
    epochs=150,
    batch=2,
    imgsz=1024,  # 调大尺寸，提升小图标识别率（比960更适配小目标）
    device="cpu",
    # 核心：小目标增强参数
    mosaic=1.0,  # 拼接增强，增加小目标出现概率
    mixup=0.2,  # 混合增强，提升背景鲁棒性
    hsv_h=0.05,  # 降低色调增强（避免图标颜色失真）
    hsv_s=0.3,  # 降低饱和度增强
    perspective=0.0,  # 关闭透视变换（避免图标形状变形）
    # 损失权重：提升小目标框定位精度
    box=10.0,  # 框回归损失权重（默认7.5，加大后更关注框的精准度）
    cls=1.0,  # 分类损失权重（提升图标类别区分）
    lr0=0.0005,  # 更小的学习率，避免小目标训练震荡
    val=True,
    save=True,
    project="../models",
    name="result",
)