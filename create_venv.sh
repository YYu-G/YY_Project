#!/bin/bash

echo "========================================"
echo "创建Python虚拟环境（Python 3.10以下版本）"
echo "========================================"

# 检查Python版本
python --version
if [ $? -ne 0 ]; then
    echo "错误：未找到Python，请先安装Python 3.10以下版本"
    exit 1
fi

# 检查Python版本是否为3.10以下
python -c "import sys; sys.exit(0) if sys.version_info.major == 3 and sys.version_info.minor < 10 else sys.exit(1)"
if [ $? -ne 0 ]; then
    echo "错误：Python版本需要3.10以下，当前版本可能高于3.10"
    echo "请安装Python 3.9或3.8"
    exit 1
fi

# 创建虚拟环境
echo "正在创建虚拟环境..."
python -m venv venv
if [ $? -ne 0 ]; then
    echo "错误：创建虚拟环境失败"
    exit 1
fi

# 激活虚拟环境
echo "虚拟环境创建成功！"
echo ""
echo "激活虚拟环境命令："
echo "source venv/bin/activate"
echo ""
echo "安装依赖命令："
echo "pip install -r requirements.txt"
echo ""
echo "或者使用国内镜像源加速："
echo "pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
echo ""
