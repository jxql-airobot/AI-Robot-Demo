# V1/V2 Windows 版演示启动脚本
# 统一 UTF-8 控制台编码, 解决中文乱码
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath 'F:\AI-Projects\AI-Robot-Demo'
python main.py
