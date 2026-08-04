#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent_rag.py — Agent + RAG 集成测试 (V5.3)
================================================
验证：memory_tool 写记忆时同步建向量；Agent 混合检索能语义召回
关键词不同但语义相近的问题。

用法（WSL，需已安装 sentence-transformers 并下载模型）：
    python3 agent/test_agent_rag.py
"""

import os
import sys
import tempfile

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(AGENT_DIR)
for p in (AGENT_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402


def main():
    tmp_dir = tempfile.mkdtemp(prefix="agent_rag_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    agent = Agent(backend="local", db_path=db_path, planner=MockPlanPlanner())

    assert agent.retriever is not None, "RAG 未初始化，请确认已安装 sentence-transformers"

    # 1. memory_tool 写记忆 → 向量同步
    tool = agent.registry["memory_tool"]
    out = tool.run(
        {
            "write": {
                "topic": "红色零件",
                "content": "位于右侧区域",
                "category": "物体信息",
            }
        }
    )
    assert out["ok"], f"写记忆失败: {out}"
    print(f"[OK] 写记忆并同步向量: {out['message']}")

    # 2. Agent 混合检索：语义相近问题
    rows = agent.retrieve_memories("那个红色东西在哪里", top_k=3)
    print(f"[RAG] 查询「那个红色东西在哪里」:")
    for r in rows:
        print(f"  [{r['source']}] {r['topic']} -> {r['content']}")
    assert rows, "没有检索到记忆"
    assert "红色零件" in rows[0]["topic"], f"语义召回失败: {rows[0]}"
    print("[OK] 语义召回红色零件")

    # 3. memory_tool 语义查询动作
    out2 = tool.run({"semantic": "那个红色东西在哪里"})
    assert out2["ok"], f"语义查询失败: {out2}"
    print(f"[OK] memory_tool 语义查询: {out2['message']}")

    # 4. Agent 规划上下文注入（mock 规划器能从记忆文本提取新位置）
    out3 = tool.run(
        {"write": {"topic": "B区域", "content": "检测区右侧", "category": "环境信息"}}
    )
    assert out3["ok"]
    resp = agent.handle("把蓝色零件送到B区域")
    print(f"[OK] 规划上下文注入 -> 目标: {resp['plan']['goal']}")

    agent.close()
    print("\ntest_agent_rag 全部通过")


if __name__ == "__main__":
    main()
