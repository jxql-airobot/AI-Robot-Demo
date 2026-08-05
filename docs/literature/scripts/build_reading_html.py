# -*- coding: utf-8 -*-
"""把所有中文阅读笔记合成一个排版好的网页，双击即可在浏览器阅读。"""

import html as html_mod
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(_BASE, "reading_notes")
OUT = os.path.join(_BASE, "论文中文导读.html")


def esc(t):
    t = t.replace("**", "").replace("`", "")
    return html_mod.escape(t, quote=False)


def md_to_html(md):
    out = []
    in_list = False
    for raw in md.splitlines():
        s = raw.strip()
        if not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if s.startswith("```"):
            continue
        if s.startswith("# "):
            t = f"<h1>{esc(s[2:])}</h1>"
        elif s.startswith("## "):
            t = f"<h2>{esc(s[3:])}</h2>"
        elif s.startswith("### "):
            t = f"<h3>{esc(s[4:])}</h3>"
        elif s == "---":
            t = "<hr/>"
        elif s.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{esc(s[2:])}</li>")
            continue
        elif s.startswith("> "):
            t = f"<blockquote>{esc(s[2:])}</blockquote>"
        elif s.startswith("|"):
            t = f"<p>{esc(s.strip('|'))}</p>"
        else:
            t = f"<p>{esc(s)}</p>"
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(t)
    if in_list:
        out.append("</ul>")
    return "".join(out)


files = [
    "00_索引.md",
    "yao-2023-react.md", "ahn-2022-saycan.md", "huang-2022-inner-monologue.md",
    "lewis-2020-rag.md", "driess-2023-palm-e.md", "brohan-2023-rt2.md",
    "vemprala-2023-chatgpt-for-robotics.md",
    "ahmed-2016-software-architectures-robotics.md",
    "liu-2024-embodied-ai-survey.md", "firoozi-2023-foundation-models-robotics.md",
    "tsushima-2025-task-planning-factory-robot.md",
    "martinez-2013-ros-complete-reference.md",
]

body = []
for fn in files:
    p = os.path.join(NOTES_DIR, fn)
    if not os.path.exists(p):
        continue
    with open(p, encoding="utf-8") as f:
        body.append(f'<div class="paper">{md_to_html(f.read())}</div>')

css = """
body { font-family: "Microsoft YaHei","PingFang SC",sans-serif; max-width: 860px;
       margin: 0 auto; padding: 32px 24px; font-size: 17px; line-height: 1.9;
       color: #222; background: #fff; }
h1 { font-size: 26px; text-align: center; margin: 12px 0 6px; }
h2 { font-size: 21px; border-left: 5px solid #2f6fbf; padding-left: 10px;
     margin-top: 26px; color: #1f3f66; }
h3 { font-size: 18px; color: #333; margin-top: 18px; }
p { margin: 8px 0; text-align: justify; }
ul { margin: 6px 0 6px 4px; padding-left: 22px; }
li { margin: 4px 0; }
blockquote { border-left: 4px solid #ccc; margin: 10px 0; padding: 4px 14px;
             color: #555; background: #f7f7f7; }
hr { border: none; border-top: 2px dashed #bbb; margin: 26px 0; }
.paper { page-break-after: always; }
.paper > h1:first-child { display: none; }
.title-banner { background: #2f6fbf; color: #fff; padding: 18px 22px;
                border-radius: 8px; margin-bottom: 26px; }
.title-banner h1 { margin: 0; color: #fff; }
.title-banner p { margin: 6px 0 0; font-size: 15px; color: #dce9f7; }
"""

doc = (
    '<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
    "<title>AI-Robot-Demo 论文中文导读</title>"
    f"<style>{css}</style></head><body>"
    '<div class="title-banner">'
    "<h1>AI-Robot-Demo 论文中文导读</h1>"
    "<p>12 篇文献的中文阅读笔记合集 · 个人学习资料 · 2026-08-05</p>"
    "</div>"
    + "".join(body)
    + "</body></html>"
)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print("已生成:", OUT)
