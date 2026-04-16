# YY_Project - 计算机视觉自动化测试系统

这是一个基于PyCharm开发的Python项目，包含YOLO目标检测、PaddleOCR文字识别和自动化测试系统。现在已配置为可以在VSCode中运行。

## 项目结构

```
YY_Project/
├── .idea/                    # PyCharm项目配置
├── auto_system/auto_test/    # 自动化测试系统
│   ├── adb_controller.py
│   ├── model_controller.py
│   ├── model_trainer.py
│   ├── process_controller.py
│   └── test_controller.py
├── datasets/                 # 数据集
├── paddleOCR/                # PaddleOCR文字识别
├── yolo/                     # YOLO目标检测训练结果和模型
├── main.py                   # 主入口文件
├── requirements.txt          # Python依赖
├── check_python_version.py   # Python版本检查工具
└── .vscode/                  # VSCode配置
    ├── settings.json
    └── launch.json
```

## 环境要求

- **Python版本**: 3.10以下版本（推荐Python 3.8或3.9）
- **操作系统**: Windows/Linux/macOS
- **VSCode**: 最新版本，安装Python扩展

## 在VSCode中启动项目

### 1. 打开项目
1. 打开VSCode
2. 点击"文件" → "打开文件夹"
3. 选择 `d:\uid02310\Desktop\YY_Project` 目录

### 2. 检查Python版本
运行以下命令检查Python版本：
```bash
python check_python_version.py
```
或者直接在VSCode中运行该脚本。

### 3. 创建虚拟环境（推荐）
在VSCode终端中执行：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 激活虚拟环境（Linux/macOS）
source venv/bin/activate
```

### 4. 安装依赖
```bash
# 安装基础依赖
pip install -r requirements.txt

# 或者逐个安装主要依赖
pip install numpy opencv-python pillow matplotlib pandas
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics
pip install paddlepaddle paddleocr
```

### 5. 设置Python解释器
1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Python: Select Interpreter"
3. 选择虚拟环境中的Python解释器：
   - Windows: `./venv/Scripts/python.exe`
   - Linux/macOS: `./venv/bin/python`

### 6. 运行项目
#### 方法一：使用VSCode调试
1. 打开 `main.py` 文件
2. 按 `F5` 或点击运行按钮
3. 选择 "Python: 运行 main.py" 配置

#### 方法二：使用终端
```bash
# 激活虚拟环境后
python main.py
```

#### 方法三：运行测试控制器
```bash
python auto_system/auto_test/test_controller.py
```

### 7. 调试配置
VSCode已预配置以下调试选项：
- **Python: 运行 main.py** - 运行主程序
- **Python: 运行测试控制器** - 运行自动化测试控制器
- **Python: 调试当前文件** - 调试当前打开的文件
- **Python: 运行 pytest 测试** - 运行测试（需要创建测试文件）

## 项目功能模块

### 1. YOLO目标检测
- 位置：`yolo/` 目录
- 包含训练好的模型和训练结果
- 支持目标检测任务

### 2. PaddleOCR文字识别
- 位置：`paddleOCR/` 目录
- 支持中英文文字识别
- 可与YOLO结合使用

### 3. 自动化测试系统
- 位置：`auto_system/auto_test/` 目录
- 包含多个控制器模块：
  - `adb_controller.py`: ADB设备控制
  - `model_controller.py`: 模型控制
  - `process_controller.py`: 流程控制
  - `test_controller.py`: 测试控制器主类

## 常见问题

### 1. Python版本问题
如果Python版本高于3.10，需要降级到3.9或3.8：
1. 下载Python 3.9安装包
2. 安装时勾选"Add Python to PATH"
3. 在VSCode中选择正确的Python解释器

### 2. 依赖安装失败
如果某些包安装失败，可以尝试：
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者单独安装有问题的包
pip install torch==1.13.1 torchvision==0.14.1 --index-url https://download.pytorch.org/whl/cpu
```

### 3. VSCode无法识别虚拟环境
1. 重启VSCode
2. 确保虚拟环境已创建
3. 使用命令面板重新选择解释器

### 4. 导入错误
如果出现导入错误，确保项目根目录在Python路径中：
```python
import sys
sys.path.append('/path/to/YY_Project')
```

## 开发建议

1. **使用虚拟环境**：避免污染系统Python环境
2. **定期更新依赖**：使用 `pip list --outdated` 检查更新
3. **代码格式化**：VSCode已配置Black格式化，保存时自动格式化
4. **代码检查**：使用flake8进行代码质量检查
5. **版本控制**：建议使用Git进行版本管理

## 联系方式

如有问题，请检查项目文档或联系项目维护者。

---

**注意**: 本项目从PyCharm迁移到VSCode，已配置完整的开发环境。如有PyCharm特定配置需要迁移，请参考VSCode对应功能。
