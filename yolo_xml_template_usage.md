# YOLO车载屏幕自动化测试XML模板使用说明

## 概述

本XML模板专为车载屏幕自动化测试系统设计，集成了YOLO模型识别功能，支持图片匹配、坐标操作、多轮循环测试和条件判断等多种测试场景。

## 模板结构

### 1. 全局配置 (GlobalConfig)
- **YOLO模型配置**: 指定模型路径、置信度阈值、设备等参数
- **设备配置**: 定义测试设备的类型、分辨率、连接方式
- **截图配置**: 配置截图保存路径和命名规则
- **执行配置**: 设置重试次数、超时时间等执行参数

### 2. 元素定义库 (ElementLibrary)
支持三种元素定义方式：
- **ImageElement**: 基于图片匹配的元素
- **YoloElement**: 基于YOLO模型识别的元素
- **CoordinateElement**: 基于坐标的元素

### 3. 测试用例 (TestCase)
每个测试用例包含：
- **Preconditions**: 测试前置条件
- **TestSteps**: 测试步骤序列
- **ExpectedResults**: 预期结果
- **Postconditions**: 测试后置操作

### 4. 支持的操作类型

#### 基本操作
- `capture_screen`: 截取屏幕
- `click_image`: 点击图片匹配的元素
- `click_coordinate`: 点击指定坐标
- `yolo_click`: 使用YOLO识别并点击元素
- `input_text`: 输入文本
- `press_key`: 模拟按键
- `swipe`: 滑动操作
- `wait`: 等待指定时间

#### 验证操作
- `yolo_verify`: 验证YOLO识别结果
- `image_verify`: 验证图片匹配结果
- `ocr_verify`: 验证OCR识别文本
- `assert`: 断言条件

#### 控制结构
- `Loop`: 循环执行测试步骤
- `Condition`: 条件判断分支

### 5. 高级功能

#### 循环测试
```xml
<Loop times="5" name="播放控制循环测试">
    <Step id="2.${iteration}" name="播放控制第${iteration}次">
        <!-- 测试步骤 -->
    </Step>
</Loop>
```

#### 条件判断
```xml
<Condition type="ocr_condition">
    <Check>
        <Text>当前温度</Text>
        <Region x="100" y="200" width="300" height="100"/>
        <ExtractPattern>(\d+)°C</ExtractPattern>
    </Check>
    <If condition="extracted_value > 25">
        <!-- 温度高于25度时的操作 -->
    </If>
    <Else>
        <!-- 其他情况的操作 -->
    </Else>
</Condition>
```

#### 数据驱动测试
```xml
<DataDrivenTests>
    <TestData id="navigation_destinations">
        <DataRow>
            <Destination>北京市天安门广场</Destination>
            <ExpectedResult>success</ExpectedResult>
        </DataRow>
        <!-- 更多测试数据 -->
    </TestData>
    
    <TestTemplate id="navigation_test_template">
        <!-- 测试模板定义 -->
    </TestTemplate>
</DataDrivenTests>
```

## 使用示例

### 示例1: 使用YOLO识别并点击元素
```xml
<Step id="1" name="识别并点击空调按钮">
    <Action type="yolo_click">
        <ElementRef>climate_control</ElementRef>
        <Confidence>0.7</Confidence>
    </Action>
    <Wait duration="2000"/>
</Step>
```

### 示例2: 图片匹配点击
```xml
<Step id="2" name="点击导航图标">
    <Action type="click_image">
        <ElementRef>nav_icon</ElementRef>
        <ClickType>single</ClickType>
        <Offset x="10" y="10"/>
    </Action>
    <Wait duration="2000"/>
</Step>
```

### 示例3: 坐标点击
```xml
<Step id="3" name="点击屏幕中心">
    <Action type="click_coordinate">
        <X>960</X>
        <Y>360</Y>
        <Description>屏幕中心点</Description>
    </Action>
</Step>
```

### 示例4: 验证操作
```xml
<Step id="4" name="验证元素存在">
    <Verification type="yolo_verify">
        <ElementRef>home_button</ElementRef>
        <ExpectedState>visible</ExpectedState>
        <Timeout>5000</Timeout>
    </Verification>
</Step>
```

## 配置说明

### YOLO模型配置
```xml
<YoloModelConfig>
    <ModelPath>./yolo/models/icon.pt</ModelPath>
    <ConfidenceThreshold>0.6</ConfidenceThreshold>
    <IOUThreshold>0.5</IOUThreshold>
    <Device>cpu</Device>
    <ImageSize>1024</ImageSize>
</YoloModelConfig>
```

### 元素定义
```xml
<ImageElement id="home_button" description="主界面按钮">
    <ImagePath>./reference_images/home_button.png</ImagePath>
    <Confidence>0.8</Confidence>
    <Region x="0" y="0" width="1920" height="720"/>
</ImageElement>

<YoloElement id="climate_control" description="空调控制按钮">
    <ClassName>climate_button</ClassName>
    <Confidence>0.7</Confidence>
</YoloElement>

<CoordinateElement id="screen_center" description="屏幕中心点">
    <X>960</X>
    <Y>360</Y>
</CoordinateElement>
```

## 最佳实践

1. **元素管理**: 将常用元素定义在ElementLibrary中，便于复用
2. **错误处理**: 合理设置重试次数和超时时间
3. **截图记录**: 重要步骤前后保存截图，便于问题排查
4. **模块化设计**: 将复杂测试拆分为多个小步骤
5. **数据驱动**: 使用数据驱动测试提高测试覆盖率

## 扩展建议

1. **自定义操作**: 可根据需要扩展新的操作类型
2. **插件系统**: 支持第三方插件扩展功能
3. **报告定制**: 自定义测试报告格式和内容
4. **集成CI/CD**: 与持续集成系统集成

## 注意事项

1. 确保YOLO模型文件路径正确
2. 参考图片需要与测试设备屏幕分辨率匹配
3. 坐标操作需要考虑不同设备的分辨率差异
4. 合理设置等待时间，避免因加载延迟导致测试失败
5. 定期更新参考图片和YOLO模型，适应界面变化

## 故障排除

### 常见问题
1. **元素识别失败**: 检查图片质量、置信度阈值设置
2. **点击位置偏差**: 检查坐标计算或使用偏移量调整
3. **测试超时**: 调整超时时间或优化测试步骤
4. **模型加载失败**: 检查模型文件路径和格式

### 调试建议
1. 启用详细日志记录
2. 保存失败时的截图和识别结果
3. 使用可视化工具查看YOLO识别结果
4. 分步执行测试，定位问题步骤

---

*本模板设计考虑了代码解析的便利性，使用标准的XML结构，便于使用各种XML解析库进行处理。*
