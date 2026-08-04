# -*- coding: utf-8 -*-
"""
vector_store.py — SQLite 向量存储 (V5.3)
========================================
新表 memories_embeddings 存记忆副本 + 向量 BLOB；
numpy 余弦相似度检索 top-k（demo 数据量小，无需向量数据库服务）。
"""

import sqlite3

import numpy as np


class VectorStore:
    """记忆向量表"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                embedding BLOB NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def rebuild(self, memory_store, embedder):
        """把记忆库全部记忆嵌入并重建向量表，返回嵌入条数"""
        rows = memory_store.all_memories()
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM memories_embeddings")
        if not rows:
            conn.commit()
            conn.close()
            return 0
        texts = [f"{topic}，{content}" for topic, content, _ in rows]
        vecs = embedder.embed(texts)
        for (topic, content, category), vec in zip(rows, vecs):
            conn.execute(
                "INSERT INTO memories_embeddings (topic, content, category, embedding)"
                " VALUES (?, ?, ?, ?)",
                (topic, content, category, vec.astype(np.float32).tobytes()),
            )
        conn.commit()
        conn.close()
        return len(rows)

    def search(self, query_vec, top_k=5):
        """按余弦相似度返回 top-k 记忆（query_vec 需归一化）"""
        query = np.asarray(query_vec, dtype=np.float32).reshape(-1)
        q_norm = np.linalg.norm(query)
        if q_norm == 0:
            return []
        query = query / q_norm

        conn = sqlite3.connect(self.db_path)
        cur = conn.execute(
            "SELECT topic, content, category, embedding FROM memories_embeddings"
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []

        topics, contents, categories, vecs = [], [], [], []
        for topic, content, category, blob in rows:
            topics.append(topic)
            contents.append(content)
            categories.append(category)
            vecs.append(np.frombuffer(blob, dtype=np.float32))
        matrix = np.stack(vecs)
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0] = 1.0
        matrix = matrix / norms[:, None]
        scores = matrix @ query
        top = np.argsort(scores)[::-1][:top_k]
        return [
            {
                "topic": topics[i],
                "content": contents[i],
                "category": categories[i],
                "score": round(float(scores[i]), 4),
            }
            for i in top
        ]
