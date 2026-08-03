# -*- coding: utf-8 -*-
"""
llm.py — 大模型接口 (DeepSeek 作为机器人"大脑")
================================================
职责:
    接收用户自然语言任务，输出结构化 JSON 机器人动作指令。

两种规划器(接口一致，都是 plan_task(user_input) -> dict):
    DeepSeekPlanner: 调用 DeepSeek API 真正理解任务(需要 API Key)
    MockPlanner:     内置关键词匹配的离线规划器(无 Key 测试用)

未来升级:
    这里可以加入任务记忆、环境信息，让规划更智能。
"""

import json
import os

from dotenv import load_dotenv

# 允许的动作类型(与 robot.py 对齐)
SUPPORTED_ACTIONS = ("move", "pick", "place", "scan", "status")

# 系统提示词模板: {memory} 会被替换成记忆上下文
SYSTEM_PROMPT = """你现在是机器人任务规划AI。
你拥有以下环境记忆：
{memory}

请结合用户任务和已有记忆生成JSON动作。

可执行的动作:
1. move   - 把某个零件从一个工位移动到另一个工位
   示例: {"action": "move", "object": "红色零件", "target": "检测区"}
2. pick   - 抓取某个零件
   示例: {"action": "pick", "object": "红色零件"}
3. place  - 把夹爪中的零件放到某工位
   示例: {"action": "place", "target": "成品区"}
4. scan   - 扫描工作台，报告所有零件的当前位置
   示例: {"action": "scan"}
5. status - 报告机器人当前状态
   示例: {"action": "status"}

工位: 上料区、检测区、成品区（还可以使用记忆中出现的新位置）
零件: 红色零件、蓝色零件、绿色零件

要求:
- 只输出一个 JSON 对象，不要输出任何解释或 markdown。
- 如果指令无法理解，输出: {"action": "error", "message": "简要说明原因"}
- 如果用户没有指定目标位置，请根据常识选择合理的工位。"""


def load_config():
    """读取 .env 配置(API Key、Base URL、模型名)"""
    load_dotenv()  # 从项目根目录的 .env 读取
    return {
        "api_key": os.getenv("DEEPSEEK_API_KEY", "").strip(),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
    }


class DeepSeekPlanner:
    """调用 DeepSeek API 的任务规划器"""

    def __init__(self):
        from openai import OpenAI  # 延迟导入，避免未安装时报错

        cfg = load_config()
        if not cfg["api_key"]:
            raise RuntimeError(
                "未找到 DEEPSEEK_API_KEY。"
                "请在项目目录复制 .env.example 为 .env 并填入密钥，"
                "或使用 python main.py --mock 进行离线演示。"
            )
        if not cfg["api_key"].startswith("sk-") or not cfg["api_key"].isascii():
            raise RuntimeError(
                "DEEPSEEK_API_KEY 看起来不是有效密钥"
                "(应为 sk- 开头的 ASCII 字符串)。"
                "请在 .env 中填入真实密钥，或使用 python main.py --mock 进行离线演示。"
            )
        self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        self.model = cfg["model"]

    def plan_task(self, user_input, memory_text=""):
        """自然语言 + 记忆上下文 -> JSON 动作指令"""
        memory_section = memory_text if memory_text else "（暂无记忆）"
        system_prompt = SYSTEM_PROMPT.replace("{memory}", memory_section)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.1,  # 低温让输出更稳定
                response_format={"type": "json_object"},  # DeepSeek JSON 输出模式
            )
            text = response.choices[0].message.content
            return self._parse_json(text)
        except Exception as exc:  # 网络错误 / API 鉴权失败等
            return {
                "action": "error",
                "message": f"调用 DeepSeek API 失败: {exc}",
            }

    @staticmethod
    def _parse_json(text):
        """把模型返回的文本解析成 dict，失败时返回 error 指令"""
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("不是 JSON 对象")
            return data
        except (json.JSONDecodeError, ValueError):
            return {"action": "error", "message": f"模型返回了无法解析的内容: {text}"}


class MockPlanner:
    """离线规划器: 用关键词匹配模拟 AI 理解(接口与 DeepSeekPlanner 一致)"""

    PARTS = ["红色零件", "蓝色零件", "绿色零件"]
    STATIONS = ["上料区", "检测区", "成品区"]

    def plan_task(self, user_input, memory_text=""):
        """离线规划器: 也支持从记忆文本中识别新位置"""
        text = user_input
        part = next((p for p in self.PARTS if p in text), None)
        station = next((s for s in self.STATIONS if s in text), None)

        # V2: 从记忆文本中提取主题(形如 "- A区域：生产线左侧（环境信息）")
        topics = []
        for line in memory_text.splitlines():
            line = line.strip()
            if line.startswith("- ") and "：" in line:
                topics.append(line[2:].split("：")[0])
        if station is None:
            station = next((t for t in topics if t in text), None)

        if "扫描" in text or "查看" in text or "状态" in text:
            return {"action": "scan"}
        if "抓取" in text or "捡" in text or "拿" in text:
            if part:
                return {"action": "pick", "object": part}
        if "移动" in text or "放" in text or "送到" in text or "运到" in text:
            if part and station:
                return {"action": "move", "object": part, "target": station}
            if station:
                # 用户没指定具体零件时，默认拿第一个零件
                return {"action": "move", "object": "红色零件", "target": station}
            if part:
                return {"action": "pick", "object": part}
        return {
            "action": "error",
            "message": f"无法理解任务: {user_input}，试试\"把红色零件移动到检测区\"",
        }


def build_planner(mock=False):
    """工厂函数: 根据参数选择规划器"""
    if mock:
        return MockPlanner()
    return DeepSeekPlanner()
