# 开发操作约定（重要）

> 本文记录本项目中反复踩过的坑与必须遵守的操作约定。
> 更新日期：2026-08-06（来源：全家桶启动器引号问题完整排查）

## 1. 跨 shell 调用禁止内联引号命令（铁律）

### 问题背景

本项目涉及多层 shell 调用：Windows PowerShell / cmd ↔ WSL（wsl.exe）↔
bash ↔ ROS2 / Python。经反复验证，**PowerShell 向 `wsl.exe` 传递含
引号或特殊字符的命令时，参数会被 Windows 命令行解析剥掉或拆分**：

- 双引号 `"..."` 常被剥掉；
- 嵌套引号（如 `bash -lc "python3 -c \"...\""`）会被拆成多个参数；
- 特殊字符 `&`、`|`、`>`、`$`、`2>&1`、中文全角引号都可能被破坏；
- 表现：命令不执行、bash 收到截断命令、进程卡住无输出、日志文件不创建。

典型错误写法（**禁止**）：

```powershell
# 错误：wsl.exe 参数含引号/特殊字符，可能不执行或卡住
wsl.exe -d Ubuntu-22.04 -e bash -lc "source ...; pkill ...; setsid nohup ... &"
Start-Process -FilePath 'wsl.exe' -ArgumentList '...' # 部分会话下命令根本不执行
```

### 正确做法

1. **把命令写成脚本文件**（`scripts/*.sh` / `*.ps1`），调用时只传简单路径：

   ```powershell
   wsl.exe -d Ubuntu-22.04 -e bash /mnt/f/AI-Projects/AI-Robot-Demo/scripts/xxx.sh
   ```

2. 需要后台常驻进程时，在脚本**内部**用：

   ```bash
   setsid nohup <命令> > /tmp/xxx.log 2>&1 &
   ```

   `setsid` 让进程脱离 WSL 会话，`wsl.exe` 退出后仍保持运行
   （仅 `nohup ... &` 在 wsl 退出后会被清理）。

3. 启动器（VBS / PowerShell Launcher / 快捷方式）**只调用脚本路径**，
   不内联任何命令；桌面快捷方式用 `wscript.exe` + VBS 隐藏运行最可靠。

4. 清理进程时，`pkill -f` 的模式用 `[x]` 正则技巧，避免匹配并杀掉
   调用命令自身：

   ```bash
   pkill -9 -f 'gzserve[r]'      # 匹配 gzserver，不匹配含 'gzserve[r]' 的自身命令行
   pkill -9 -f 'streamlit ru[n]'
   ```

## 2. 已落地的实现（以此为准）

- `AI_Robot_Demo_Background.vbs`：全家桶快捷方式入口（wscript 隐藏运行），
  内部只调用脚本路径；
- `scripts/launcher_background_sim.sh`：setsid 后台启动 ROS2 + Gazebo；
- `scripts/launcher_background_gui.sh`：setsid 后台启动 Streamlit GUI；
- `scripts/reset_system.sh`：彻底清理并重启仿真（避免多个 launch 冲突）。

不要重新引入内联 `wsl.exe bash -lc "..."` 的写法。

## 3. PowerShell 脚本编码

`.ps1` 文件含中文时**必须保存为 UTF-8 with BOM**：

- Windows PowerShell 5.1（`powershell.exe`）对无 BOM 的 UTF-8 按 ANSI/GBK
  解析，中文与反引号转义会被乱码破坏，导致 `Missing closing '}'` 等
  假语法错误；
- 修改 `.ps1` 后统一执行一次：

  ```powershell
  $f = '路径.ps1'
  $c = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)
  [System.IO.File]::WriteAllText($f, $c, (New-Object System.Text.UTF8Encoding($true)))
  ```

## 4. 环境相关注意事项

- 从 Codex / 非交互会话调用 `wsl.exe`（尤其 `Start-Process`）行为与用户
  桌面双击不同：命令可能不执行或立即退出，**不能据此判定用户环境好坏**；
- 多次用不同方式启动仿真会产生多个 `ros2 launch` 实例互相冲突，遇到
  节点反复消失/端口占用时，先执行 `scripts/reset_system.sh` 再重启；
- GUI 端口固定 `8501`；仿真由 `robot_controller / brain_node / vision_node`
  三个节点组成，缺一不可（`pgrep -c` 在 WSL 下偶发误报，以 `ps aux`
  为准）。

