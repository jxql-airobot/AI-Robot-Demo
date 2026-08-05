# -*- coding: utf-8 -*-
"""把中文阅读笔记写入 Zotero，作为各论文条目的子笔记。

笔记文件：docs/literature/reading_notes/*.md
目标：Zotero 中每篇论文条目下挂一个"中文笔记"子笔记，双击即可阅读。

前提：Zotero 处于关闭状态。
用法：python docs/literature/scripts/add_notes_to_zotero.py
"""

import os
import random
import re
import sqlite3

DB = r"F:\ZoteroData\zotero.sqlite"
NOTES_DIR = r"F:\AI-Projects\AI-Robot-Demo\docs\literature\reading_notes"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
NOW = "2026-08-05 10:00:00"

# 笔记文件名关键字 -> 论文标题关键字（用于匹配 Zotero 条目）
MATCH = [
    ("yao-2023-react", "ReAct"),
    ("ahn-2022-saycan", "Do As I Can"),
    ("huang-2022-inner-monologue", "Inner Monologue"),
    ("lewis-2020-rag", "Retrieval-Augmented Generation"),
    ("driess-2023-palm-e", "PaLM-E"),
    ("brohan-2023-rt2", "RT-2"),
    ("vemprala-2023-chatgpt-for-robotics", "ChatGPT for Robotics"),
    ("ahmed-2016-software-architectures-robotics", "Software Architectures for Robotics"),
    ("liu-2024-embodied-ai-survey", "Aligning Cyber Space"),
    ("firoozi-2023-foundation-models-robotics", "Foundation Models in Robotics"),
    ("tsushima-2025-task-planning-factory-robot", "Task Planning for a Factory Robot"),
    ("martinez-2013-ros-complete-reference", "ROS: The Complete Reference"),
]


def gen_key(used):
    while True:
        k = "".join(random.choice(UPPER) for _ in range(8))
        if k not in used:
            return k


def md_to_html(md):
    """极简 Markdown -> Zotero 可接受的 HTML。"""
    out = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if s.startswith("```"):
            continue
        if s.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p><strong>{esc(s[2:])}</strong></p>")
        elif s.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p><strong>{esc(s[3:])}</strong></p>")
        elif s.startswith("### "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p><strong>{esc(s[4:])}</strong></p>")
        elif s == "---":
            if in_list:
                out.append("</ul>"); in_list = False
            out.append("<p>————————————————</p>")
        elif s.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{esc(s[2:])}</li>")
        elif s.startswith("> "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<blockquote>{esc(s[2:])}</blockquote>")
        elif s.startswith("|"):
            if in_list:
                out.append("</ul>"); in_list = False
            row = s.strip("|")
            out.append(f"<p>{esc(row)}</p>")
        else:
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p>{esc(s)}</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)


def esc(t):
    t = t.replace("**", "")
    t = t.replace("`", "")
    return t


con = sqlite3.connect(DB)
cur = con.cursor()
used = {k for (k,) in cur.execute("SELECT key FROM items")}


def find_item_id(keyword):
    for iid, title in cur.execute(
        "SELECT i.itemID, "
        "(SELECT value FROM itemDataValues v JOIN itemData d ON d.valueID=v.valueID "
        " WHERE d.itemID=i.itemID AND d.fieldID=1) "
        "FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID "
        "WHERE it.typeName != 'attachment'"
    ):
        if title and keyword.lower() in title.lower():
            return iid
    return None


def add_note(parent_id, title, html):
    k = gen_key(used)
    used.add(k)
    cur.execute(
        "INSERT INTO items(itemTypeID, dateAdded, dateModified, clientDateModified, libraryID, key, version, synced) "
        "VALUES (28,?,?,?,1,?,1,0)",
        (NOW, NOW, NOW, k))
    nid = cur.lastrowid
    cur.execute(
        "INSERT INTO itemNotes(itemID, parentItemID, note, title) VALUES (?,?,?,?)",
        (nid, parent_id, html, title))
    return nid


added = 0
for fname_key, title_key in MATCH:
    fpath = os.path.join(NOTES_DIR, fname_key + ".md")
    if not os.path.exists(fpath):
        print("缺笔记文件:", fpath)
        continue
    iid = find_item_id(title_key)
    if not iid:
        print("找不到对应条目:", title_key)
        continue
    with open(fpath, encoding="utf-8") as f:
        html = md_to_html(f.read())
    add_note(iid, "中文阅读笔记", html)
    added += 1
    print("已挂载:", title_key)

# 总索引笔记（独立笔记）
idx_path = os.path.join(NOTES_DIR, "00_索引.md")
if os.path.exists(idx_path):
    with open(idx_path, encoding="utf-8") as f:
        idx_html = md_to_html(f.read())
    add_note(None, "文献库中文笔记索引", idx_html)
    print("已挂载: 文献库中文笔记索引")
    added += 1

con.commit()
print("共写入笔记:", added)
con.close()
