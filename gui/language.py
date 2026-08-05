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
TITLE_WITH_VERSION = "AI Robot 智能体 V5.2"
SIDEBAR_TITLE = "🤖 AI Robot 智能体"
SIDEBAR_CAPTION = "V5.2 · Streamlit 客户端（Agent 模式）"
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

# ---------- V6.0: 机器人后端选择 ----------
ROBOT_BACKEND_LABEL = "机器人后端"
ROBOT_BACKEND_GAZEBO = "Gazebo"
ROBOT_BACKEND_ROBOTSTUDIO = "RobotStudio"
ROBOT_RS_CONNECTED = "已连接：RobotStudio（Mock）"
ROBOT_RS_HINT = "RobotStudio 模式：config backend=mock（本地）或 real（连接虚拟控制器）"
ROBOT_RS_JOINTS = "关节位置"
ROBOT_RS_CONNECT_STATE = "连接状态"
ROBOT_RS_LAST_ACTION = "最后动作"
ROBOT_RS_LAST_RESULT = "最后返回结果"
ROBOT_RS_TCP = "TCP 连接状态"
STATUS_BACKEND = "当前后端：{backend}"

# ---------- V6.2: 系统状态 ----------
SYS_STATUS_TITLE = "系统状态"
SYS_LLM = "LLM 规划器"
SYS_RAG = "RAG 语义检索"
SYS_ROBOT = "机器人连接"
SYS_LLM_OK = "DeepSeek"
SYS_LLM_MOCK = "离线 Mock"
SYS_RAG_OK = "可用"
SYS_RAG_DEGRADED = "降级(关键词)"
SYS_ROBOT_OK = "已连接"
SYS_ROBOT_OFF = "未连接"

# ---------- 标签页 ----------
TAB_CHAT = "💬 任务对话"
TAB_WORKSPACE = "🗂 工作台状态"
TAB_MEMORY = "🧠 记忆查看"
TAB_VISION = "👁 视觉感知"
TAB_ROBOT = "🤖 机器人状态"
TAB_EXPERIMENT = "📊 实验分析"
TAB_REPLAY = "🔄 任务回放"
TAB_SYSTEM = "ℹ️ 系统信息"

# ---------- 任务对话区 ----------
CHAT_SUBHEADER = "任务对话"
CHAT_CAPTION = "输入自然语言任务，Agent 会生成可解释计划并调用工具执行。"
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

# ---------- V5.2 Agent 可解释 Plan ----------
AGENT_SPINNER = "Agent 正在生成计划并调用工具执行..."
AGENT_PLAN_TASK_ANALYSIS = "任务分析"
AGENT_PLAN_GOAL = "目标"
AGENT_PLAN_STEPS = "执行步骤"
AGENT_PLAN_CURRENT_STATE = "当前状态"
AGENT_PLAN_TOOL = "工具"
AGENT_PLAN_ARGS = "参数"
AGENT_RESULT_TITLE = "执行结果"
AGENT_FINAL = "总结"

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
MEM_CAPTION = "查看和查询记忆，支持 RAG 语义检索；暂不提供删除功能。"
MEM_SEARCH_LABEL = "关键词查询"
MEM_SEARCH_PLACEHOLDER = "语义检索：例如：那个红色东西在哪里"
MEM_FILTER_LABEL = "分类筛选"
MEM_CATEGORIES = ["环境信息", "物体信息", "用户知识"]
MEM_EMPTY = "暂无记忆。"
MEM_COUNT = "共 {count} 条"
MEM_COL_TOPIC = "主题"
MEM_COL_CONTENT = "内容"
MEM_COL_CATEGORY = "分类"
MEM_COL_SOURCE = "来源"

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

# ---------- V6.2: 机器人状态页增强 ----------
ROB_LAST_TASK = "当前任务"
ROB_LAST_EXEC = "执行时间"
ROB_LAST_SUCCESS = "成功状态"
