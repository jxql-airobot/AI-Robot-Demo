# -*- coding: utf-8 -*-
"""
planner.py — 可解释 Plan 生成器 (V5.2)
======================================
两种规划器，接口一致 plan(task, context) -> dict：
  - DeepSeekPlanPlanner：调用 DeepSeek API 生成 Plan（任务分析/目标/执行步骤/当前状态）
  - MockPlanPlanner：关键词匹配的离线规划器

只输出可解释 Plan，不输出 LLM 完整思考链。
"""

import json

from agent.plan_schema import error_plan, normalize_plan


SYSTEM_PROMPT = """你是 AI Robot 智能体的任务规划器。
根据用户任务、会话上下文和可用工具，生成一个可解释的 JSON 任务计划。
只输出 JSON，不要输出任何解释或思考过程。

字段说明:
- task_analysis: 一句话分析用户意图
- goal: 明确的目标
- steps: 执行步骤数组，每步 {"tool": 工具名, "args": {...}, "purpose": "这步要做什么"}
- current_state: 当前已知状态（使用上下文；未知则写"未知"）

可用工具:
{tools}

要求:
- steps 必须使用上面列出的工具名
- args 必须符合工具参数格式
- 不要输出思考过程，只输出计划"""


def _tool_descriptions(registry):
    lines = []
    for name, tool in registry.items():
        lines.append(f"- {name}: {tool.description}")
    return "\n".join(lines)


class DeepSeekPlanPlanner:
    """调用 DeepSeek 生成可解释 Plan"""

    def __init__(self, registry):
        from openai import OpenAI  # 延迟导入
        from llm import load_config  # 只读复用 V1 配置读取

        cfg = load_config()
        self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        self.model = cfg["model"]
        self.tools_text = _tool_descriptions(registry)

    def plan(self, task, context):
        system_prompt = SYSTEM_PROMPT.replace("{tools}", self.tools_text)
        user_text = f"用户任务: {task}\n\n会话上下文:\n{context.format_for_planner()}"
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            return normalize_plan(data)
        except Exception as exc:
            return error_plan(
                f"调用 DeepSeek 失败: {exc}", current_state=context.current_state or "未知"
            )


class MockPlanPlanner:
    """离线规划器：关键词匹配生成 Plan（接口与 DeepSeekPlanPlanner 一致）"""

    PARTS = ["红色零件", "蓝色零件", "绿色零件"]
    STATIONS = ["上料区", "检测区", "成品区"]

    def plan(self, task, context):
        text = task
        part = next((p for p in self.PARTS if p in text), None)
        station = next((s for s in self.STATIONS if s in text), None)
        current_state = context.current_state or "未知"

        # 记住指令 -> 写入记忆
        if text.startswith("记住") or text.startswith("记忆"):
            parsed = self._parse_remember(text)
            if parsed:
                topic, content = parsed
                return {
                    "task_analysis": "用户希望保存一条环境/物体记忆",
                    "goal": f"保存记忆: {topic} -> {content}",
                    "steps": [
                        {
                            "tool": "memory_tool",
                            "args": {
                                "write": {
                                    "topic": topic,
                                    "content": content,
                                    "category": "环境信息" if self._is_env(text) else "用户知识",
                                }
                            },
                            "purpose": f"保存新记忆 {topic}",
                        },
                        {
                            "tool": "environment_tool",
                            "args": {"memories": True},
                            "purpose": "刷新环境信息",
                        },
                    ],
                    "current_state": current_state,
                }

        # 扫描/查看/状态 -> 视觉 + 环境
        if "扫描" in text or "查看" in text or "状态" in text:
            return {
                "task_analysis": "用户要求扫描工作台并获取当前状态",
                "goal": "扫描工作台，报告所有零件位置与工位状态",
                "steps": [
                    {
                        "tool": "vision_tool",
                        "args": {"scan": True},
                        "purpose": "扫描视觉识别结果",
                    },
                    {
                        "tool": "environment_tool",
                        "args": {"status": True},
                        "purpose": "获取工作台状态",
                    },
                ],
                "current_state": current_state,
            }

        # 抓取/捡/拿 -> pick
        if "抓取" in text or "捡" in text or "拿" in text:
            if part:
                return {
                    "task_analysis": "用户要求抓取指定零件",
                    "goal": f"抓取 {part}",
                    "steps": [
                        {
                            "tool": "robot_tool",
                            "args": {"action": "pick", "object": part},
                            "purpose": f"抓取 {part}",
                        }
                    ],
                    "current_state": current_state,
                }

        # 移动/放/送到 -> move
        if "移动" in text or "放" in text or "送到" in text or "运到" in text:
            if part and station:
                return {
                    "task_analysis": "用户要求移动零件到指定工位",
                    "goal": f"把 {part} 移动到 {station}",
                    "steps": [
                        {
                            "tool": "robot_tool",
                            "args": {"action": "move", "object": part, "target": station},
                            "purpose": f"把 {part} 从当前位置移动到 {station}",
                        }
                    ],
                    "current_state": current_state,
                }
            if part:
                return {
                    "task_analysis": "用户要求移动零件但未指定工位",
                    "goal": f"抓取 {part}",
                    "steps": [
                        {
                            "tool": "robot_tool",
                            "args": {"action": "pick", "object": part},
                            "purpose": f"先抓取 {part}",
                        }
                    ],
                    "current_state": current_state,
                }

        # 在哪里/位置 -> 视觉 + 环境
        if "哪里" in text or "位置" in text or "在哪" in text:
            steps = [
                {
                    "tool": "vision_tool",
                    "args": {"scan": True},
                    "purpose": f"查找{'零件' if not part else part}的位置",
                }
            ]
            if part:
                steps.append(
                    {
                        "tool": "environment_tool",
                        "args": {"status": True},
                        "purpose": "核对工作台状态",
                    }
                )
            return {
                "task_analysis": "用户询问零件位置",
                "goal": f"定位{'零件' if not part else part}",
                "steps": steps,
                "current_state": current_state,
            }

        return error_plan(f"无法理解任务: {task}", current_state=current_state)

    @staticmethod
    def _parse_remember(text):
        body = text[2:].lstrip("：:，, ")
        for sep in ("=", "是", "在", "位于"):
            if sep in body:
                topic, content = body.split(sep, 1)
                topic = topic.strip()
                content = content.strip()
                if topic and content:
                    return topic, content
        return None

    @staticmethod
    def _is_env(text):
        return any(k in text for k in ("区域", "位置", "车间", "工位", "侧", "线", "台"))


def build_plan_planner(registry, mock=False):
    """工厂：有有效 DeepSeek Key 用真实规划器，否则离线 Mock"""
    if mock:
        return MockPlanPlanner()
    try:
        from llm import load_config

        cfg = load_config()
        key = cfg.get("api_key", "")
        if key.startswith("sk-") and key.isascii():
            return DeepSeekPlanPlanner(registry)
    except Exception:
        pass
    return MockPlanPlanner()
