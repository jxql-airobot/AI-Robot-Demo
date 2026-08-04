#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rag.py — RAG 语义检索测试 (V5.3)
=====================================
核心用例：记忆「红色零件位于右侧区域」，用关键词不同但语义相近的
问题「那个红色东西在哪里」查询，应正确召回红色零件。

用法（WSL，首次会自动下载模型）：
    python3 agent/rag/test_rag.py
"""

import os
import sys
import tempfile

RAG_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(RAG_DIR)
REPO_ROOT = os.path.dirname(AGENT_DIR)
for p in (AGENT_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from memory import MemoryStore  # noqa: E402
from agent.rag.embedder import Embedder  # noqa: E402
from agent.rag.model_download import ensure_model  # noqa: E402
from agent.rag.retriever import HybridRetriever  # noqa: E402
from agent.rag.vector_store import VectorStore  # noqa: E402


def main():
    # 1. 确保模型已下载
    print("[RAG] 检查模型...")
    ensure_model()

    # 2. 临时记忆库 + 向量表
    tmp_dir = tempfile.mkdtemp(prefix="rag_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    memory = MemoryStore(db_path)
    memory.remember("红色零件", "位于右侧区域", "物体信息")
    memory.remember("蓝色零件", "位于中间区域", "物体信息")
    memory.remember("绿色零件", "位于左侧区域", "物体信息")
    memory.remember("A区域", "生产线左侧", "环境信息")

    embedder = Embedder()
    vector_store = VectorStore(db_path)
    count = vector_store.rebuild(memory, embedder)
    print(f"[RAG] 已嵌入 {count} 条记忆")

    # 3. 核心用例：语义相近但关键词不同
    retriever = HybridRetriever(vector_store, memory, embedder)
    query = "那个红色东西在哪里"
    rows = retriever.retrieve(query, top_k=3)
    print(f"[RAG] 查询「{query}」:")
    for row in rows:
        print(f"  [{row['source']}] {row['topic']} -> {row['content']}")

    assert rows, "语义检索没有返回任何结果"
    top = rows[0]
    assert "红色零件" in top["topic"], f"语义召回失败，top1 是: {top}"
    print("[OK] 语义相近问题正确召回「红色零件」")

    # 4. 关键词兜底（无模型时也能检索）
    kw_retriever = HybridRetriever(vector_store, memory, embedder=None)
    rows2 = kw_retriever.retrieve("红色零件", top_k=3)
    assert rows2, "关键词兜底检索失败"
    assert "红色零件" in rows2[0]["topic"], f"关键词兜底结果错误: {rows2}"
    print(f"[OK] 关键词兜底返回 {len(rows2)} 条，来源: {rows2[0]['source']}")

    print("\ntest_rag 全部通过")


if __name__ == "__main__":
    main()
