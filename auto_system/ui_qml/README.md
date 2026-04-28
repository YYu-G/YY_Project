# QML UI 原型启动说明

## 启动
在项目根目录执行：

```powershell
python auto_system/ui_qml/main_qml.py
```

## 当前能力
- 左侧导航 + 卡片化布局（QML）
- 已接入后端 `ProcessController` 执行链路
- 支持输入 XML 路径 / 模型路径并运行流程
- 结果 JSON 与日志回显

## 架构分层
- `auto_system/ui_qml/qml/`: 界面层（QML）
- `auto_system/ui_qml/backend/`: Python 桥接层（Signal/Slot）
- `auto_system/auto_test/`: 业务能力层（现有控制器）

## 下一步建议
1. 增加数据标注页（调用 `ModelController.create_dataset_with_annotation`）
2. 增加模型训练页（调用 `ModelController.train_model`）
3. 把颜色/字号/间距抽为 design tokens
