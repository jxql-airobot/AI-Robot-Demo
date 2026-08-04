# -*- coding: utf-8 -*-
"""
language.py — 界面文字集中管理 (V5.1 中文化)
============================================
所有用户可见文字统一放在这里, app.py 不散落中文文本。
后续切换语言时, 只需替换本文件内容即可。

专业名词保留英文, 不翻译:
AI / Agent / Robot / ROS2 / Gazebo / Streamlit / DeepSeek / JSON / API / Memory / GUI / Python
"""

# ---------- 页面与标题 ----------
TITLE = "AI Robot 智能体"
TITLE_WITH_VERSION = "AI Robot 智能体 V5.1"
SIDEBAR_TITLE = "🤖 AI Robot 智能体"
SIDEBAR_CAPTION = "V5.1 · Streamlit 客户端"
MAIN_CAPTION = "Streamlit 独立客户端 · 不修改 V1-V4 任何代码与节点"

# ---------- 侧边栏: 模式与连接 ----------
MODE_LABEL = "后端模式"
MODE_ROS2 = "ROS2 模式"
MODE_LOCAL = "本地模式"
MODE_NAMES = {"ROS2": "ROS2 模式", "Local": "本地模式"}
BUTTON_CONNECT = "连接 / 重新连接"
INFO_LOCAL_NOT_AVAILABLE = "本地模式为后续版本功能，V5.1 暂未开放。"
ERROR_CONNECT_FAILED = "ROS2 连接失败：{error}"
HINT_CHECK_ENV = "请确认：① 已在 WSL 中 source 过 ROS2 环境；② 仿真系统已启动。"
STATUS_CONNECTED = "已连接：{mode}"
HINT_SIM_REQUIRED = "仿真系统需已启动（ros2 launch ai_robot demo_v4.launch.py）"

# ---------- 标签页 ----------
TAB_CHAT = "💬 任务对话"
TAB_WORKSPACE = "🗂 工作台状态"
TAB_MEMORY = "🧠 记忆查看"
TAB_VISION = "👁 视觉感知"
TAB_ROBOT = "🤖 机器人状态"

# ---------- 任务对话区 ----------
CHAT_SUBHEADER = "任务对话"
CHAT_CAPTION = "输入自然语言任务，AI 大脑规划后由机器人执行。"
CHAT_EXAMPLES_TITLE = "示例指令"
CHAT_EXAMPLE_TASKS = [
    "扫描工作台",
    "红色零件在哪里",
    "把蓝色零件放到成品区",
    "记住：A区域在生产线左侧",
]
CHAT_INPUT_PLACEHOLDER = "下达任务，例如：把红色零件移动到检测区"
CHAT_SPINNER = "AI 大脑规划与机器人执行中..."
CHAT_NO_RESPONSE = "（未收到状态反馈，请确认仿真系统已启动）"

# ---------- 工作台状态区 ----------
WS_SUBHEADER = "工作台状态"
BUTTON_REFRESH = "刷新"
WS_NO_DATA = "暂无状态数据。发送任务或等待仿真系统输出。"
WS_LAST_UPDATE = "最近更新：{time}"
WS_TABLE_TITLE = "各工位零件分布："
WS_RAW_EXPANDER = "原始状态文本"
WS_EMPTY = "（空）"

# ---------- 记忆查看区 ----------
MEM_SUBHEADER = "记忆查看（只读）"
MEM_CAPTION = "查看和查询 SQLite 记忆；V5.1 暂不提供删除功能。"
MEM_SEARCH_LABEL = "关键词查询"
MEM_SEARCH_PLACEHOLDER = "例如：零件 / 区域 / 检测区"
MEM_FILTER_LABEL = "分类筛选"
MEM_CATEGORIES = ["环境信息", "物体信息", "用户知识"]
MEM_EMPTY = "暂无记忆。"
MEM_COUNT = "共 {count} 条"
MEM_COL_TOPIC = "主题"
MEM_COL_CONTENT = "内容"
MEM_COL_CATEGORY = "分类"

# ---------- 视觉感知区 ----------
VIS_SUBHEADER = "视觉感知（识别结果）"
VIS_CAPTION = "第一版仅展示识别结果；实时视频流在后续迭代中实现。"
VIS_NO_DATA = "暂无视觉识别结果（需要 Gazebo 相机 + vision_node 运行）。"
VIS_PARTS_TITLE = "识别到的零件与位置："
VIS_NONE = "当前画面未识别到零件。"
VIS_RAW_EXPANDER = "原始识别结果"

# ---------- 机器人状态区 ----------
ROB_SUBHEADER = "机器人状态（里程计）"
ROB_NO_DATA = "暂无里程计数据（需要 Gazebo 仿真运行）。"
ROB_METRIC_X = "X 坐标"
ROB_METRIC_Y = "Y 坐标"
ROB_METRIC_YAW = "朝向 Yaw"
ROB_METRIC_LINEAR = "线速度"
ROB_METRIC_ANGULAR = "角速度"
