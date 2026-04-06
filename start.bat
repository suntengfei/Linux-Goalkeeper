@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   Shell监控与AI安全助手 - 启动脚本
echo ========================================

cd /d "%~dp0"

if not exist "config.yaml" (
    echo 错误: 找不到 config.yaml 配置文件
    echo 请复制 config.yaml.example 为 config.yaml 并修改配置
    pause
    exit /b 1
)

echo [1/3] 检查Python环境...
where python >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   Python版本: %PYTHON_VERSION%

echo [2/3] 安装依赖...
pip install -q -r requirements.txt

echo [3/3] 启动服务...
echo   WebSocket服务: ws://localhost:8765
echo   Web界面: http://localhost:8080
echo.

python -m server.main
echo 按任意键退出...
pause >nul
