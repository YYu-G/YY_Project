"""
完整流程测试脚本
测试从原素材到数据标注到应用标注数据集训练得到模型的全过程
"""

import sys
import os
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_system.auto_test.model_trainer import ModelTrainer, AnnotationTool
import shutil


def test_full_pipeline():
    """测试完整流程：素材 -> 标注 -> 训练 -> 模型"""
    
    print("=" * 80)
    print("完整流程测试")
    print("=" * 80)
    
    # 配置参数
    project_root = "d:/uid02310/Desktop/YY_Project"
    dataset_name = "test_full_pipeline"
    
    # 类别定义
    class_names = ['airConditioner', 'home', 'music', 'power', 'setting']
    
    # 原始素材目录
    source_images_dir = "d:/uid02310/Desktop/YY_Project/yolo/data/source"
    
    # 初始化模型训练器
    print("\n[步骤 1] 初始化模型训练器...")
    trainer = ModelTrainer(
        project_root=project_root,
        dataset_name=dataset_name
    )
    print(f"✓ 模型训练器初始化完成")
    print(f"  数据集路径: {trainer.dataset_path}")
    
    # 准备数据集（上传图片）
    print("\n[步骤 2] 准备数据集...")
    
    # 获取原始图片
    source_dir = Path(source_images_dir)
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_paths = []
    
    for ext in image_extensions:
        image_paths.extend(source_dir.glob(f"*{ext}"))
        image_paths.extend(source_dir.glob(f"*{ext.upper()}"))
    
    image_paths = [str(p) for p in image_paths]
    
    if not image_paths:
        print(f"✗ 未找到原始图片，跳过此步骤")
        print("  使用现有数据集进行测试")
    else:
        print(f"  找到 {len(image_paths)} 张原始图片")
        
        # 上传图片到数据集
        upload_stats = trainer.upload_images(image_paths, split_ratio=0.8)
        print(f"✓ 图片上传完成:")
        print(f"  总计: {upload_stats['total']} 张")
        print(f"  训练集: {upload_stats['train']} 张")
        print(f"  验证集: {upload_stats['val']} 张")
    
    # 创建数据集配置文件
    print("\n[步骤 3] 创建数据集配置文件...")
    yaml_path = trainer.create_dataset_yaml(class_names)
    print(f"✓ 数据集配置文件创建完成:")
    print(f"  路径: {yaml_path}")
    print(f"  类别: {class_names}")
    
    # 手动标注部分（使用API方式，不启动GUI）
    print("\n[步骤 4] 数据标注（API方式）...")
    
    # 获取训练集图片
    train_images_dir = trainer.dataset_path / "images" / "train"
    train_image_paths = list(train_images_dir.glob("*.png")) + list(train_images_dir.glob("*.jpg"))
    
    if not train_image_paths:
        print(f"✗ 未找到训练集图片，跳过标注步骤")
    else:
        print(f"  找到 {len(train_image_paths)} 张训练集图片")
        
        # 为每张图片添加示例标注（模拟标注）
        annotated_count = 0
        for img_path in train_image_paths[:3]:  # 只标注前3张图片作为示例
            # 读取图片获取尺寸
            import cv2
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            
            height, width = img.shape[:2]
            
            # 创建示例标注（在图片中心位置）
            annotations = [
                {
                    'class_id': 0,
                    'bbox': [width//4, height//4, width//2, height//2]
                }
            ]
            
            # 保存标注
            success = trainer.annotate_image(
                image_path=str(img_path),
                annotations=annotations,
                class_names=class_names
            )
            
            if success:
                annotated_count += 1
                print(f"  ✓ 标注完成: {img_path.name}")
        
        print(f"✓ 数据标注完成: {annotated_count} 张图片")
    
    # 训练模型
    print("\n[步骤 5] 训练YOLOv11模型...")
    
    # 使用较小的训练参数进行快速测试
    train_params = {
        'epochs': 10,  # 减少训练轮数
        'batch': 8,
        'imgsz': 640,
        'device': 'cpu',
        'workers': 4,
        'patience': 5,
        'name': 'test_pipeline_result'
    }
    
    print(f"  训练参数: {train_params}")
    print("  开始训练...")
    
    train_result = trainer.train_model(
        dataset_yaml=yaml_path,
        model_size='n',  # 使用最小的模型
        custom_params=train_params
    )
    
    if train_result['success']:
        print(f"✓ 模型训练完成:")
        print(f"  模型路径: {train_result['model_path']}")
        print(f"  结果路径: {train_result['results_path']}")
        print(f"  训练指标:")
        for metric_name, metric_value in train_result['metrics'].items():
            print(f"    {metric_name}: {metric_value:.4f}")
    else:
        print(f"✗ 模型训练失败: {train_result['message']}")
        return False
    
    # 可视化训练结果
    print("\n[步骤 6] 可视化训练结果...")
    visualizations = trainer.visualize_training_results(train_result['results_path'])
    
    if visualizations:
        print(f"✓ 训练结果可视化完成:")
        for viz_name, viz_path in visualizations.items():
            print(f"  {viz_name}: {viz_path}")
    else:
        print(f"✗ 训练结果可视化失败")
    
    # 评估模型
    print("\n[步骤 7] 评估模型性能...")
    eval_result = trainer.evaluate_model(
        model_path=train_result['model_path'],
        dataset_yaml=yaml_path
    )
    
    if eval_result['success']:
        print(f"✓ 模型评估完成:")
        print(f"  评估指标:")
        for metric_name, metric_value in eval_result['metrics'].items():
            print(f"    {metric_name}: {metric_value:.4f}")
    else:
        print(f"✗ 模型评估失败: {eval_result['message']}")
    
    # 预测测试
    print("\n[步骤 8] 模型预测测试...")
    
    # 使用验证集图片进行预测
    val_images_dir = trainer.dataset_path / "images" / "val"
    val_image_paths = list(val_images_dir.glob("*.png")) + list(val_images_dir.glob("*.jpg"))
    
    if val_image_paths:
        test_image = str(val_image_paths[0])
        print(f"  测试图片: {Path(test_image).name}")
        
        detections = trainer.predict_image(
            model_path=train_result['model_path'],
            image_path=test_image,
            conf_threshold=0.5,
            save_result=False
        )
        
        print(f"✓ 预测完成，检测到 {len(detections)} 个目标:")
        for i, det in enumerate(detections[:5], 1):  # 只显示前5个
            print(f"  {i}. {det['class_name']} (置信度: {det['confidence']:.4f})")
    else:
        print(f"✗ 未找到验证集图片，跳过预测测试")
    
    # 导出模型
    print("\n[步骤 9] 导出模型...")
    export_success = trainer.export_model(
        model_path=train_result['model_path'],
        format='onnx'
    )
    
    if export_success:
        print(f"✓ 模型导出完成 (ONNX格式)")
    else:
        print(f"✗ 模型导出失败")
    
    # 获取训练摘要
    print("\n[步骤 10] 生成训练摘要...")
    summary = trainer.get_training_summary()
    
    if summary:
        print(f"✓ 训练摘要:")
        print(f"  状态: {summary['status']}")
        print(f"  数据集名称: {summary['dataset_name']}")
        print(f"  数据集路径: {summary['dataset_path']}")
        print(f"  模型路径: {summary['model_path']}")
    
    print("\n" + "=" * 80)
    print("完整流程测试完成！")
    print("=" * 80)
    
    return True


def test_annotation_tool():
    """测试标注工具（GUI方式）"""
    
    print("\n" + "=" * 80)
    print("标注工具测试（GUI方式）")
    print("=" * 80)
    
    # 测试图片路径
    test_image_path = "../../datasets/yolo-pageAndBottom/images/train/airConditioner.png"
    
    # 类别定义
    class_names = ['airConditioner', 'home', 'music', 'power', 'setting']
    
    print(f"\n测试图片: {test_image_path}")
    print(f"类别: {class_names}")
    
    # 创建标注工具
    tool = AnnotationTool(
        image_path=test_image_path,
        class_names=class_names
    )
    
    print("\n标注工具已启动，请在GUI窗口中进行标注")
    print("操作说明:")
    print("  - 鼠标左键拖动: 绘制标注框")
    print("  - 数字键 1-5: 切换类别")
    print("  - S键: 保存标注")
    print("  - C键: 清除当前标注")
    print("  - Q键: 退出")
    
    # 运行标注工具
    annotations = tool.run()
    
    # 保存标注
    if annotations:
        tool.save_annotations()
        print(f"\n✓ 标注完成，共标注 {len(annotations)} 个目标")
    else:
        print("\n未进行任何标注")
    
    print("\n" + "=" * 80)
    print("标注工具测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='完整流程测试脚本')
    parser.add_argument('--mode', type=str, default='full', 
                       choices=['full', 'annotation'], 
                       help='测试模式: full=完整流程, annotation=仅标注工具')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'full':
            success = test_full_pipeline()
            sys.exit(0 if success else 1)
        elif args.mode == 'annotation':
            test_annotation_tool()
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
