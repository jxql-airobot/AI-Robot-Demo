# -*- coding: utf-8 -*-
"""
memory.py — 机器人记忆系统 (SQLite)
====================================
V2 新增功能：让机器人具备简单记忆能力。

数据保存在 database.db（SQLite 数据库，Python 自带 sqlite3，无需安装）。
支持三类记忆：环境信息 / 物体信息 / 用户知识。

接口：
    remember(topic, content, category)  保存一条记忆
    search(query, limit)                按关键词查询相关记忆
    all_memories()                      返回全部记忆
    format_prompt(rows)                 把记忆格式化成给 AI 的文本
"""

import sqlite3

DB_PATH = "database.db"

# 记忆分类
CATEGORIES = ("环境信息", "物体信息", "用户知识")


class MemoryStore:
    """SQLite 记忆仓库"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """创建数据库和记忆表（首次运行自动执行）"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,      -- 主题/实体名，如 A区域
                content TEXT NOT NULL,    -- 内容，如 生产线左侧
                category TEXT NOT NULL,   -- 分类：环境信息/物体信息/用户知识
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.commit()
        conn.close()

    def remember(self, topic, content, category="用户知识"):
        """保存一条记忆"""
        if category not in CATEGORIES:
            category = "用户知识"
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO memories (topic, content, category) VALUES (?, ?, ?)",
            (topic, content, category),
        )
        conn.commit()
        conn.close()
        return True

    def search(self, query, limit=5):
        """查询相关记忆（模糊匹配主题和内容，也支持主题出现在提问里的情况）"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.execute(
            """
            SELECT topic, content, category FROM memories
            WHERE topic LIKE ? OR content LIKE ? OR ? LIKE '%' || topic || '%'
            ORDER BY id DESC LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", query, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def all_memories(self):
        """返回全部记忆（按保存顺序）"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.execute(
            "SELECT topic, content, category FROM memories ORDER BY id"
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def format_prompt(self, rows):
        """把记忆记录格式化成 AI 能读的文本"""
        if not rows:
            return "（暂无相关记忆）"
        lines = []
        for topic, content, category in rows:
            lines.append(f"- {topic}：{content}（{category}）")
        return "\n".join(lines)
