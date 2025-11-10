@echo off
echo 正在启动小红书文案生成器...

REM 激活虚拟环境（如果存在）
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate
)

REM 运行GUI应用程序
python gui_app.py

echo 程序已退出。
pause