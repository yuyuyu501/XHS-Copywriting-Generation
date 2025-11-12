# 小红书文案生成器

这是一个用于生成小红书教育类文案的GUI应用程序。

## 功能特点

1. 自动生成学校介绍文案
2. 将生成的JSON文案转换为Word文档
3. 图形化用户界面，操作简单
4. 支持断点续传功能

## 安装和运行

### 方法一：直接运行（推荐）

1. 确保已安装Python 3.8或更高版本
2. 安装依赖包：
   ```
   pip install -r requirements.txt
   ```
3. 运行GUI应用程序：
   ```
   python gui_app.py
   ```
   或双击运行 `run_gui.bat`

### 方法二：打包成独立应用程序

1. 安装PyInstaller：
   ```
   pip install pyinstaller
   ```
2. 打包应用程序：
   ```
   pyinstaller --onefile --windowed gui_app.py
   ```
3. 在 `dist` 目录下找到生成的 `gui_app.exe` 文件

## 使用说明

1. 选择原始文案文件（JSON格式）
2. 选择生成文案文件的保存位置
3. 点击"开始生成文案"按钮
4. 生成完成后，可选择转换为Word文档

## 项目结构

```
代码/
├── 主干/
│   ├── 模型/
│   │   ├── Doubao_seed_1_6.py
│   │   └── prompts.py
│   └── 生成文案.py
├── 支线/
│   └── 教育/
│       ├── json转word.py
│       ├── 文案检查与替换.py
│       └── 爬取图片.py
├── gui_app.py          # GUI应用程序
├── main.py             # 命令行主程序
├── requirements.txt    # 依赖包列表
├── run_gui.bat         # 运行脚本
└── build_app.bat       # 打包脚本
```

## 注意事项

1. 需要网络连接以调用AI模型
2. 首次运行可能需要登录小红书账号
3. 生成的文案会自动进行违禁词检查和替换