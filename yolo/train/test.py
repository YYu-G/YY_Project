from ultralytics import YOLO
import cv2

# 【这次训练好的 正确路径】
MODEL_PATH = "D:/uid02310/Desktop/YY_Project/auto_system/yolo/test9_20260512_164959/best.pt"

# 你的测试图路径
IMAGE_PATH = "D:/uid02310/Desktop/YY_Project/auto_system/images"

# 加载模型
model = YOLO(MODEL_PATH)

# 推理
results = model.predict(
    source=IMAGE_PATH,
    imgsz=1024,
    conf=0.2,     # 不用0.001那么低，0.1就够了
    iou=0.45,
    device="cpu"
)


# ======================
# ✅ 我帮你修改这里（正确打印所有图片的所有结果）
# ======================
print("\n=== 检测结果 ===")

# 遍历 所有图片 的结果
for i, result in enumerate(results):
    print(f"\n--- 第 {i+1} 张图片 ---")
    
    # 遍历这张图片里 所有检测框
    if len(result.boxes) == 0:
        print("未检测到目标")
    else:
        for box in result.boxes:
            cls_id = int(box.cls)
            conf = float(box.conf)
            print(f"类别: {cls_id}, 置信度: {conf:.2f}")