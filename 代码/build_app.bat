@echo off
echo 正在打包小红书文案生成器...

REM 创建虚拟环境
python -m venv venv

REM 激活虚拟环境
call venv\Scripts\activate

REM 安装依赖
pip install -r requirements.txt

REM 使用PyInstaller打包GUI应用程序
pip install pyinstaller
pyinstaller --onefile --windowed gui_app.py

echo 打包完成！可执行文件位于 dist/gui_app.exe

REM 暂停以查看结果
pause