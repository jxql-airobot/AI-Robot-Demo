# -*- coding: utf-8 -*-
"""修复：把 Zotero 条目/分类 key 统一改为 8 位大写字母+数字。

原因：Zotero 9 的存储目录解析要求 key 匹配 /^[A-Z0-9]{8}$/，
直接写入的小写混合 key 会导致"无法找到附件"。

前提：Zotero 处于关闭状态；执行前已备份数据库。
用法：python docs/literature/scripts/fix_keys_uppercase.py
"""

import os
import random
import re
import shutil
import sqlite3

DB = r"F:\ZoteroData\zotero.sqlite"
STORAGE = r"F:\ZoteroData\storage"
PAPERS = r"F:\AI-Robot-Demo-Literature\papers"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def gen_key(used):
    while True:
        k = "".join(random.choice(UPPER) for _ in range(8))
        if k not in used:
            return k


def find_pdf_source(fname):
    """在 Zotero storage 与 F 盘文献库中查找同名 PDF，返回绝对路径或 None。"""
    for base in (STORAGE, PAPERS):
        for root, _, files in os.walk(base):
            if fname in files:
                return os.path.join(root, fname)
    return None


con = sqlite3.connect(DB)
cur = con.cursor()
used = {k for (k,) in cur.execute("SELECT key FROM items UNION SELECT key FROM collections")}

# 1) 附件条目换 key（先只改数据库）
attachments = cur.execute(
    "SELECT ia.itemID, i.key, ia.path FROM itemAttachments ia "
    "JOIN items i ON i.itemID = ia.itemID"
).fetchall()
renames = []
for item_id, old_key, path in attachments:
    nk = gen_key(used)
    used.add(nk)
    cur.execute("UPDATE items SET key=? WHERE itemID=?", (nk, item_id))
    fname = path[len("storage:"):]
    renames.append((old_key, nk, fname))

# 2) 论文条目与分类换 key（先取列表再更新，避免边遍历边更新导致截断）
paper_ids = [r[0] for r in cur.execute(
    "SELECT i.itemID FROM items i "
    "LEFT JOIN itemAttachments ia ON ia.itemID = i.itemID "
    "WHERE ia.itemID IS NULL"
)]
for item_id in paper_ids:
    nk = gen_key(used)
    used.add(nk)
    cur.execute("UPDATE items SET key=? WHERE itemID=?", (nk, item_id))

col_ids = [r[0] for r in cur.execute("SELECT collectionID FROM collections")]
for col_id in col_ids:
    nk = gen_key(used)
    used.add(nk)
    cur.execute("UPDATE collections SET key=? WHERE collectionID=?", (nk, col_id))

con.commit()

# 3) 重建 storage 目录：删旧目录，从源文件复制到新 key 目录
for old_key, nk, fname in renames:
    old_dir = os.path.join(STORAGE, old_key)
    if os.path.isdir(old_dir):
        shutil.rmtree(old_dir, ignore_errors=True)
    src = find_pdf_source(fname)
    dest_dir = os.path.join(STORAGE, nk)
    os.makedirs(dest_dir, exist_ok=True)
    if src:
        shutil.copy2(src, os.path.join(dest_dir, fname))
        print("重建:", nk, "<-", src)
    else:
        print("警告: 找不到源文件", fname)

# 4) 校验
bad = 0
for (k,) in cur.execute("SELECT key FROM items UNION SELECT key FROM collections"):
    if not re.match(r"^[A-Z0-9]{8}$", k):
        bad += 1
        print("非法 key:", k)
missing = 0
for (key, path) in cur.execute(
    "SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID"
):
    fname = path[len("storage:"):]
    if not os.path.exists(os.path.join(STORAGE, key, fname)):
        missing += 1
        print("缺失:", key, fname)
print("非法 key 数:", bad)
print("缺失附件数:", missing)
con.close()
