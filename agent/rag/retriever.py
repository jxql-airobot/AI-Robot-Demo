# -*- coding: utf-8 -*-
"""
retriever.py — 混合检索 (V5.3)
==============================
向量语义检索为主，V2 关键词检索兜底，按 (topic, content) 去重。
每条结果带 source（语义检索 / 关键词检索），供 GUI 展示来源。
"""


class HybridRetriever:
    """混合检索器"""

    def __init__(self, vector_store, memory, embedder=None):
        self.vector_store = vector_store
        self.memory = memory
        self.embedder = embedder

    def retrieve(self, query, top_k=5):
        """返回 [{"topic", "content", "category", "source"}, ...]"""
        merged = []
        seen = set()

        # 1. 语义检索（模型可用时）
        if self.embedder is not None and self.embedder.available:
            try:
                query_vec = self.embedder.embed(query)
                for row in self.vector_store.search(query_vec, top_k=top_k):
                    key = (row["topic"], row["content"])
                    if key not in seen:
                        seen.add(key)
                        merged.append(
                            {
                                "topic": row["topic"],
                                "content": row["content"],
                                "category": row["category"],
                                "source": "语义检索",
                            }
                        )
            except Exception:
                pass  # 语义检索失败时静默降级

        # 2. 关键词兜底（V2 原样）
        for topic, content, category in self.memory.search(query, limit=top_k):
            key = (topic, content)
            if key not in seen:
                seen.add(key)
                merged.append(
                    {
                        "topic": topic,
                        "content": content,
                        "category": category,
                        "source": "关键词检索",
                    }
                )
        return merged
