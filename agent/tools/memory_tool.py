# -*- coding: utf-8 -*-
"""
memory_tool.py — 记忆工具 (V5.2)
================================
复用 V2 的 memory.py（只读导入，不修改）。
能力：查询 / 保存 / 列出记忆。
"""

from agent.tools.base import BaseTool


class MemoryTool(BaseTool):
    """记忆工具"""

    name = "memory_tool"
    description = (
        "查询/保存/列出记忆。"
        "args: {'query': '关键词'} 或 {'write': {'topic': ..., 'content': ..., 'category': ...}}"
        " 或 {'list': true}"
    )

    def __init__(self, memory, vector_store=None, embedder=None, retriever=None):
        self.memory = memory
        self.vector_store = vector_store
        self.embedder = embedder
        self.retriever = retriever

    def run(self, args):
        if args.get("write"):
            w = args["write"]
            topic = str(w.get("topic", "")).strip()
            content = str(w.get("content", "")).strip()
            category = str(w.get("category", "用户知识"))
            if not topic or not content:
                return {"ok": False, "message": "write 需要 topic 和 content"}
            self.memory.remember(topic, content, category)
            self._sync_vector(topic, content, category)
            return {
                "ok": True,
                "result": {"topic": topic, "content": content, "category": category},
                "message": f"已保存记忆: {topic} -> {content}（{category}）",
            }
        if args.get("semantic"):
            query = str(args["semantic"])
            if self.retriever is not None:
                rows = self.retriever.retrieve(query, top_k=5)
                return {
                    "ok": True,
                    "result": {"rows": rows},
                    "message": f"语义检索到 {len(rows)} 条相关记忆",
                }
            rows = self.memory.search(query, limit=5)
            return {
                "ok": True,
                "result": {"rows": rows},
                "message": f"关键词检索到 {len(rows)} 条相关记忆",
            }
        if args.get("query"):
            rows = self.memory.search(str(args["query"]), limit=10)
            return {
                "ok": True,
                "result": {"rows": rows},
                "message": f"查询到 {len(rows)} 条相关记忆",
            }
        rows = self.memory.all_memories()
        return {
            "ok": True,
            "result": {"rows": rows},
            "message": f"共 {len(rows)} 条记忆",
        }

    def _sync_vector(self, topic, content, category):
        """V5.3: 写记忆时同步生成并保存向量（RAG 可用时）"""
        if self.vector_store is None or self.embedder is None:
            return
        try:
            vec = self.embedder.embed(f"{topic}，{content}")[0]
            self.vector_store.add(topic, content, category, vec)
        except Exception:
            pass  # 向量同步失败不影响记忆本身
