# RobotStudio 6.08 联调小白教程（8 步）

> 面向没有 ABB 使用经验的同学，按顺序照做即可。

## 第一步：安装 RobotWare

1. 从 ABB 官方渠道下载 **RobotWare 6.08.01**（见 `docs/robotware_install.md`）
2. 双击安装包，一路下一步，默认安装
3. 安装完成后，重新运行 `python robotstudio/check_environment.py`
   确认 RobotWare 出现在组件列表

## 第二步：打开 RobotStudio

1. 开始菜单搜索 **RobotStudio**，打开
2. 等待加载完成，进入主界面（基本 / 建模 / 仿真 / 控制器 标签页）

## 第三步：创建 Virtual Controller（虚拟控制器）

1. 文件 -> 新建 -> **空工作站**
2. 基本标签页 -> **机器人系统** -> **从布局创建系统**
3. 弹出窗口里选择 **RobotWare 6.08**（若列表为空说明 RobotWare 没装对）
4. 系统名填 `AI_Robot_System`，点"完成"
5. 等待右下角进度条走完，出现"系统已启动"

## 第四步：添加 ABB 机器人

1. 基本标签页 -> **ABB 模型库**（或导入模型库）
2. 选择机器人型号，如 **IRB 120**（小型六轴，最适合入门）
3. 拖到工作台，机器人出现在布局中

## 第五步：导入 RAPID 程序

1. 左下角展开 **控制器** -> `AI_Robot_System` -> 双击 **RAPID**
2. 展开任务 **T_ROB1**
3. 右键 T_ROB1 -> **导入模块** -> 选择
   `F:\AI-Projects\AI-Robot-Demo\robotstudio\rapid\socket_server.mod`
4. 出现 `SocketServer` 模块即成功

## 第六步：启动 RAPID 程序

1. RAPID 窗口点 **PP 到 main**（程序指针回到 main）
2. 点 **启动**（绿色三角）
3. 底部日志出现：`AI Agent SocketServer 等待连接 (端口 30000)`
4. 虚拟控制器默认监听 127.0.0.1:30000，不需要额外网络配置

## 第七步：Python 连接测试

1. 修改 `robotstudio/config.json`：

```json
{
  "backend": "real",
  "host": "127.0.0.1",
  "port": 30000,
  "timeout": 5
}
```

2. 运行手动测试（不经 Agent，直接验证通信）：

```bash
python robotstudio/manual_test_client.py --real
```

3. 看到 `[HOME] OK` / `[MOVEJ] OK` / `[MOVEL] OK` 即通信成功，
   RobotStudio 里机器人会真实动作

## 第八步：Agent 控制测试

1. 启动 GUI（桌面全家桶，或 `python3 -m streamlit run gui/app.py`）
2. 侧边栏「机器人后端」选 **RobotStudio**
3. 对话输入：`让机器人回到Home位置`
4. 看到可解释 Plan（任务分析/目标/执行步骤）+ 执行结果 OK +
   机器人状态页显示关节位置变化 = 完整 AI 工业机器人控制闭环 ✅
