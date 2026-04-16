#!/usr/bin/env python3
"""
测试VSCode配置是否正常工作
"""

import sys
import os

def test_imports():
    """测试关键导入"""
    print("测试Python导入...")
    
    modules_to_test = [
        ('sys', 'Python系统模块'),
        ('os', '操作系统接口'),
        ('numpy', '数值计算'),
        ('cv2', 'OpenCV计算机视觉'),
        ('PIL', '图像处理'),
        ('torch', 'PyTorch深度学习'),
    ]
    
    for module_name, description in modules_to_test:
        try:
            if module_name == 'cv2':
                import cv2
            elif module_name == 'PIL':
                from PIL import Image
            else:
                __import__(module_name)
            print(f"  ✓ {description} ({module_name}) 导入成功")
        except ImportError as e:
            print(f"  ✗ {description} ({module_name}) 导入失败: {e}")
    
    return True

def test_project_structure():
    """测试项目结构"""
    print("\n测试项目结构...")
    
    required_dirs = [
        'auto_system/auto_test',
        'datasets',
        'paddleOCR',
        'yolo',
        '.vscode',
    ]
    
    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        '.vscode/settings.json',
        '.vscode/launch.json',
    ]
    
    all_ok = True
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"  ✓ 目录存在: {dir_path}")
        else:
            print(f"  ✗ 目录缺失: {dir_path}")
            all_ok = False
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ 文件存在: {file_path}")
        else:
            print(f"  ✗ 文件缺失: {file_path}")
            all_ok = False
    
    return all_ok

def test_vscode_config():
    """测试VSCode配置"""
    print("\n测试VSCode配置...")
    
    try:
        # 检查.vscode目录
        if not os.path.exists('.vscode'):
            print("  ✗ .vscode目录不存在")
            return False
        
        # 检查settings.json
        settings_path = '.vscode/settings.json'
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                content = f.read()
                if 'python.defaultInterpreterPath' in content:
                    print("  ✓ VSCode settings.json配置正确")
                else:
                    print("  ✗ VSCode settings.json缺少Python解释器配置")
                    return False
        else:
            print("  ✗ VSCode settings.json文件不存在")
            return False
        
        # 检查launch.json
        launch_path = '.vscode/launch.json'
        if os.path.exists(launch_path):
            print("  ✓ VSCode launch.json配置存在")
        else:
            print("  ✗ VSCode launch.json文件不存在")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ VSCode配置测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("VSCode项目配置测试工具")
    print("=" * 60)
    
    print(f"Python版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    
    # 运行测试
    test_results = []
    
    test_results.append(("项目结构测试", test_project_structure()))
    test_results.append(("VSCode配置测试", test_vscode_config()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "通过" if passed else "失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！项目已准备好VSCode中运行。")
        print("\n下一步:")
        print("1. 在VSCode中打开项目文件夹")
        print("2. 按 Ctrl+Shift+P 选择Python解释器")
        print("3. 打开 main.py 按 F5 运行")
    else:
        print("❌ 部分测试失败，请检查配置。")
        print("\n建议:")
        print("1. 运行 create_venv.bat 或 create_venv.sh 创建虚拟环境")
        print("2. 安装依赖: pip install -r requirements.txt")
        print("3. 确保.vscode目录存在且配置正确")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
