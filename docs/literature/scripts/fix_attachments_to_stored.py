# -*- coding: utf-8 -*-
"""修复：把链接附件转换为 Zotero 已存储附件。

背景：直接写入的链接附件（绝对路径 F:/...）在 Zotero 9 中解析失败，
报"在此路径无法找到附件"。改为已存储附件（PDF 复制进 storage/<key>/），
不再依赖路径解析。

前提：Zotero 处于关闭状态。
用法：python docs/literature/scripts/fix_attachments_to_stored.py
"""

import os
import shutil
import sqlite3

DB = r"F:\ZoteroData\zotero.sqlite"
STORAGE = r"F:\ZoteroData\storage"

con = sqlite3.connect(DB)
cur = con.cursor()

rows = cur.execute(
    "SELECT ia.itemID, i.key, ia.path, ia.parentItemID "
    "FROM itemAttachments ia JOIN items i ON i.itemID = ia.itemID "
    "WHERE ia.linkMode = 2 AND ia.path NOT LIKE 'storage:%'"
).fetchall()

print("待转换附件数:", len(rows))
for item_id, key, path, parent_id in rows:
    src = path.replace("/", "\\")
    if not os.path.exists(src):
        print("MISS", src)
        continue
    fname = os.path.basename(src)
    dest_dir = os.path.join(STORAGE, key)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, fname)
    shutil.copy2(src, dest)
    cur.execute(
        "UPDATE itemAttachments SET linkMode=0, path=?, contentType='application/pdf' WHERE itemID=?",
        ("storage:" + fname, item_id))
    print("OK", fname, "->", dest)

con.commit()
print("剩余链接附件:",
      cur.execute("SELECT COUNT(*) FROM itemAttachments WHERE linkMode=2").fetchone()[0])
con.close()
