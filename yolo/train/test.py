from ultralytics import YOLO

# 加载训练好的模型
model = YOLO("D:/uid02310/Desktop/YY_Project/yolo/models/pageAndBotton.pt")

# 预测图片（替换成你的测试图片路径）
results = model.predict(
    source="D:/uid02310/Desktop/YY_Project/yolo/data/dataset/images/val",  # 测试图片路径
    #D:/uid02310/Desktop/YY_Project/datasets/dataset-yolo/images/val
    #D:/uid02310/Desktop/YY_Project/yolo/data/dataset/images/val
    save=True,  # 保存预测结果图片
    imgsz=640,
    conf=0.5,    # 置信度阈值（只显示>0.5的检测框）
    classes=[0,1,2]
)

# 打印预测结果
for r in results:
    for box in r.boxes:
        cls = r.names[box.cls[0].item()]
        conf = box.conf[0].item()
        print(f"检测到：{cls}，置信度：{conf:.2f}")