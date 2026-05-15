from ultralytics import YOLO
import cv2

# 【这次训练好的 正确路径】
MODEL_PATH = "D:/uid02310/Desktop/YY_Project/auto_system/yolo/runs/actual3_20260515_100135/weights/_best_ckpt.pt"
# "D:/uid02310/Desktop/YY_Project/auto_system/yolo/runs/t2_20260513_144905/weights/_best_ckpt.pt"
# "D:/uid02310/Desktop/YY_Project/auto_system/yolo/t1_20260513_141007/best.pt"
# "D:/uid02310/Desktop/YY_Project/auto_system/yolo/test_20260513_121311/best.pt"
# "D:/uid02310/Desktop/YY_Project/auto_system/yolo/actual2_20260513_123840/best.pt"

# 你的测试图路径
# IMAGE_PATH = "D:/uid02310/Desktop/YY_Project/auto_system/images"
# IMAGE_PATH = "D:/uid02310/Desktop/sucai/usage"
IMAGE_PATH="D:/uid02310/Desktop/screenshot-20260515-143506.png"

# 加载模型
model = YOLO(MODEL_PATH)

# 推理
results = model.predict(
    source=IMAGE_PATH,
    imgsz=1024,
    conf=0.1,     # 不用0.001那么低，0.1就够了
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