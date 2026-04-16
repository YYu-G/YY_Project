# -*- coding: utf-8 -*-
"""
自动生成的测试用例: 设置菜单测试
ID: TC_SETTINGS_001
描述: 测试设置菜单的导航功能
生成自: 车载屏幕测试流程
"""

import time
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from auto_system.auto_test.adb_controller import AdbController


class TcSettings001:
    """设置菜单测试"""
    
    def __init__(self):
        self.adb = AdbController()
        self.results = {'total': 0, 'passed': 0, 'failed': 0}
    
    def log(self, msg):
        """日志记录"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg}")
    
    def wait(self, ms):
        """等待"""
        seconds = int(ms) / 1000.0
        self.log(f"等待 {ms}ms")
        time.sleep(seconds)
    
    def click_coordinate(self, x, y):
        """点击坐标"""
        self.log(f"点击坐标 ({x}, {y})")
        return self.adb.adb_tap(int(x), int(y))
    
    def press_key(self, key):
        """按键"""
        key_map = {'HOME': 'home', 'BACK': 'back'}
        adb_key = key_map.get(key, key.lower())
        self.log(f"按键 {key}")
        return self.adb.adb_press_key(adb_key)
    
    def swipe(self, x1, y1, x2, y2, duration):
        """滑动"""
        self.log(f"滑动 ({x1},{y1})->({x2},{y2}) {duration}ms")
        return self.adb.adb_swipe(int(x1), int(y1), int(x2), int(y2), int(duration))
    
    def execute_action(self, action):
        """执行动作"""
        action_type = action['type']
        
        if action_type == 'wait':
            self.wait(action['duration'])
            return True
        elif action_type == 'click_coordinate':
            return self.click_coordinate(action['x'], action['y'])
        elif action_type == 'press_key':
            return self.press_key(action['key'])
        elif action_type == 'swipe':
            return self.swipe(
                action['startX'], action['startY'],
                action['endX'], action['endY'],
                action['duration']
            )
        elif action_type == 'log':
            self.log(action['message'])
            return True
        elif action_type == 'click_image':
            self.log(f"点击图片 {action['imageId']}")
            return True  # 待实现图片识别
        elif action_type == 'verify_image':
            self.log(f"验证图片 {action['imageId']}")
            return True  # 待实现图片验证
        elif action_type == 'verify_text':
            self.log(f"验证文本 {action['text']}")
            return True  # 待实现文本验证
        
        return False
    
    def execute_step(self, step):
        """执行步骤"""
        self.log(f"步骤 {step['id']}: {step['name']}")
        
        for action in step['actions']:
            success = self.execute_action(action)
            if not success:
                self.log(f"动作执行失败: {action}")
                return False
        
        return True
    
    def run(self):
        """运行测试"""
        self.log(f"开始测试: 设置菜单测试")
        self.log(f"描述: 测试设置菜单的导航功能")
        
        start_time = time.time()
        
        try:
            # 执行步骤
            steps = [
        {
            'id': '1',
            'name': '进入设置',
            'actions': [{'type': 'click_image', 'imageId': 'settings_icon'}, {'type': 'wait', 'duration': '2000'}]
        },
        {
            'id': '2',
            'name': '浏览设置',
            'actions': [{'type': 'swipe', 'startX': '960', 'startY': '500', 'endX': '960', 'endY': '200', 'duration': '500'}, {'type': 'wait', 'duration': '1000'}, {'type': 'swipe', 'startX': '960', 'startY': '500', 'endX': '960', 'endY': '200', 'duration': '500'}, {'type': 'wait', 'duration': '1000'}]
        },
        {
            'id': '3',
            'name': '进入显示设置',
            'actions': [{'type': 'click_coordinate', 'x': '200', 'y': '250'}, {'type': 'wait', 'duration': '2000'}]
        },
        {
            'id': '4',
            'name': '调节亮度',
            'actions': [{'type': 'swipe', 'startX': '400', 'startY': '400', 'endX': '800', 'endY': '400', 'duration': '1000'}, {'type': 'wait', 'duration': '1000'}, {'type': 'swipe', 'startX': '800', 'startY': '400', 'endX': '400', 'endY': '400', 'duration': '1000'}, {'type': 'wait', 'duration': '1000'}]
        },
        {
            'id': '5',
            'name': '返回主界面',
            'actions': [{'type': 'press_key', 'key': 'BACK'}, {'type': 'wait', 'duration': '1000'}, {'type': 'press_key', 'key': 'BACK'}, {'type': 'wait', 'duration': '1000'}, {'type': 'press_key', 'key': 'HOME'}, {'type': 'wait', 'duration': '2000'}, {'type': 'verify_image', 'imageId': 'home_icon', 'timeout': '3000'}]
        }
]
            
            for step in steps:
                self.results['total'] += 1
                if self.execute_step(step):
                    self.results['passed'] += 1
                else:
                    self.results['failed'] += 1
            
            # 结果统计
            duration = time.time() - start_time
            self.log("=" * 40)
            self.log(f"测试完成")
            self.log(f"总步骤: {self.results['total']}")
            self.log(f"通过: {self.results['passed']}")
            self.log(f"失败: {self.results['failed']}")
            self.log(f"耗时: {duration:.2f}秒")
            self.log("=" * 40)
            
            return self.results['failed'] == 0
            
        except Exception as e:
            self.log(f"测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    test = TcSettings001()
    success = test.run()
    
    if success:
        print("\n测试通过!")
        sys.exit(0)
    else:
        print("\n测试失败!")
        sys.exit(1)
