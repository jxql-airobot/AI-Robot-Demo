# -*- coding: utf-8 -*-
"""一次性导入脚本：把文献库 12 篇论文（含分类、标签、PDF 链接）写入 Zotero 数据库。

前提：Zotero 处于关闭状态；数据库已备份（zotero.sqlite.bak-20260805）。
用法：python docs/literature/scripts/zotero_import.py
"""

import sqlite3
import random
import os

DB = r"F:\ZoteroData\zotero.sqlite"
PDF_ROOT = r"F:/AI-Robot-Demo-Literature/papers"
KEY_ALPH = "23456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
NOW = "2026-08-05 08:00:00"


def new_key():
    return "".join(random.choice(KEY_ALPH) for _ in range(8))


con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("PRAGMA integrity_check")
assert cur.fetchone()[0] == "ok", "integrity check failed"

FID = {name: fid for fid, name in cur.execute("SELECT fieldID, fieldName FROM fields")}
TID = {name: tid for tid, name in cur.execute("SELECT itemTypeID, typeName FROM itemTypes")}
CTID = {name: cid for cid, name in cur.execute("SELECT creatorTypeID, creatorType FROM creatorTypes")}


def set_field(item_id, fname, value):
    if value is None:
        return
    cur.execute("INSERT OR IGNORE INTO itemDataValues(value) VALUES (?)", (value,))
    cur.execute("SELECT valueID FROM itemDataValues WHERE value=?", (value,))
    vid = cur.fetchone()[0]
    cur.execute("INSERT INTO itemData(itemID, fieldID, valueID) VALUES (?,?,?)",
                (item_id, FID[fname], vid))


def add_creators(item_id, names):
    for i, n in enumerate(names):
        parts = n.strip().split()
        first = " ".join(parts[:-1]) if len(parts) > 1 else ""
        last = parts[-1] if parts else ""
        cur.execute("INSERT OR IGNORE INTO creators(firstName, lastName, fieldMode) VALUES (?,?,0)",
                    (first, last))
        cur.execute("SELECT creatorID FROM creators WHERE firstName=? AND lastName=? AND fieldMode=0",
                    (first, last))
        cid = cur.fetchone()[0]
        cur.execute("INSERT INTO itemCreators(itemID, creatorID, creatorTypeID, orderIndex) VALUES (?,?,?,?)",
                    (item_id, cid, CTID["author"], i))


def add_item(itype, title, authors, date, url=None, doi=None, abstract=None,
             archive=None, archive_location=None, extra=None, extra_fields=None):
    cur.execute(
        "INSERT INTO items(itemTypeID, dateAdded, dateModified, clientDateModified, libraryID, key, version, synced) "
        "VALUES (?,?,?,?,1,?,1,0)",
        (TID[itype], NOW, NOW, NOW, new_key()))
    iid = cur.lastrowid
    set_field(iid, "title", title)
    set_field(iid, "date", date)
    set_field(iid, "abstractNote", abstract)
    if url:
        set_field(iid, "url", url)
    if doi:
        set_field(iid, "DOI", doi)
    if archive:
        set_field(iid, "archive", archive)
    if archive_location:
        set_field(iid, "archiveLocation", archive_location)
    if extra:
        set_field(iid, "extra", extra)
    if extra_fields:
        for k, v in extra_fields.items():
            if k in FID:
                set_field(iid, k, v)
    add_creators(iid, authors)
    return iid


def add_attachment(item_id, rel_path):
    path = os.path.join(PDF_ROOT, rel_path).replace("\\", "/")
    if not os.path.exists(path.replace("/", "\\")):
        print("WARN missing pdf:", path)
        return None
    cur.execute(
        "INSERT INTO items(itemTypeID, dateAdded, dateModified, clientDateModified, libraryID, key, version, synced) "
        "VALUES (?,?,?,?,1,?,1,0)",
        (TID["attachment"], NOW, NOW, NOW, new_key()))
    aid = cur.lastrowid
    cur.execute(
        "INSERT INTO itemAttachments(itemID, parentItemID, linkMode, contentType, charsetID, path, syncState) "
        "VALUES (?,?,2,'application/pdf',NULL,?,0)",
        (aid, item_id, path))
    return aid


def add_to_collections(item_id, cat):
    cur.execute("INSERT INTO collectionItems(collectionID, itemID, orderIndex) VALUES (?,?,0)",
                (COL[cat], item_id))


def ensure_tag(name):
    cur.execute("SELECT tagID FROM tags WHERE name=?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO tags(name) VALUES (?)", (name,))
    return cur.lastrowid


def add_tags(item_id, names):
    for n in names:
        cur.execute("INSERT INTO itemTags(itemID, tagID, type) VALUES (?,?,0)",
                    (item_id, ensure_tag(n),))


COL = {}
cur.execute(
    "INSERT INTO collections(collectionName, parentCollectionID, clientDateModified, libraryID, key, version, synced) "
    "VALUES (?,NULL,?,1,?,1,0)",
    ("AI-Robot-Demo Literature", NOW, new_key()))
COL["root"] = cur.lastrowid
for name in ["01 LLM Robot Planning", "02 Robot Agent", "03 RAG Knowledge",
             "04 Robot Software Architecture", "05 Embodied AI"]:
    cur.execute(
        "INSERT INTO collections(collectionName, parentCollectionID, clientDateModified, libraryID, key, version, synced) "
        "VALUES (?,?,?,1,?,1,0)",
        (name, COL["root"], NOW, new_key()))
    COL[name] = cur.lastrowid

P = []

P.append(dict(itype="preprint", cat="01 LLM Robot Planning", tags=["LLM", "Embodied AI"],
              title="PaLM-E: An Embodied Multimodal Language Model",
              authors=["Danny Driess", "Fei Xia", "Mehdi S. M. Sajjadi", "Corey Lynch", "Aakanksha Chowdhery",
                       "Brian Ichter", "Ayzaan Wahid", "Jonathan Tompson", "Quan Vuong", "Tianhe Yu",
                       "Wenlong Huang", "Yevgen Chebotar", "Pierre Sermanet", "Daniel Duckworth", "Sergey Levine",
                       "Vincent Vanhoucke", "Karol Hausman", "Marc Toussaint", "Klaus Greff", "Andy Zeng",
                       "Igor Mordatch", "Pete Florence"],
              date="2023-03-07", url="https://arxiv.org/abs/2303.03378", archive="arXiv", archive_location="2303.03378",
              abstract="Large language models have been demonstrated to perform complex tasks. However, enabling general inference in the real world, e.g. for robotics problems, raises the challenge of grounding. We propose embodied language models to directly incorporate real-world continuous sensor modalities into language models and thereby establish the link between words and percepts.",
              extra="会议：ICML 2023",
              pdf="01_LLM_Robot_Planning/driess-2023-palm-e-embodied-multimodal-language-model.pdf"))

P.append(dict(itype="preprint", cat="01 LLM Robot Planning", tags=["LLM", "Embodied AI"],
              title="RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control",
              authors=["Anthony Brohan", "Noah Brown", "Justice Carbajal", "Yevgen Chebotar", "Xi Chen",
                       "Krzysztof Choromanski", "Tianli Ding", "Danny Driess", "Avinava Dubey", "Chelsea Finn",
                       "Pete Florence", "Chuyuan Fu"],
              date="2023-07-28", url="https://arxiv.org/abs/2307.15818", archive="arXiv", archive_location="2307.15818",
              abstract="We study how vision-language models trained on Internet-scale data can be incorporated directly into end-to-end robotic control to boost generalization and enable emergent semantic reasoning. We propose to co-fine-tune state-of-the-art vision-language models on both robotic trajectory data and Internet-scale vision-language tasks.",
              extra="会议：CoRL 2023",
              pdf="01_LLM_Robot_Planning/brohan-2023-rt2-vision-language-action.pdf"))

P.append(dict(itype="journalArticle", cat="01 LLM Robot Planning",
              tags=["Robot Planning", "Industrial Robot", "Missing-PDF"],
              title="Task Planning for a Factory Robot Using Large Language Model",
              authors=["Yosuke Tsushima", "Shu Yamamoto", "Ankit A. Ravankar", "Jose V. Salazar Luces", "Yasuhisa Hirata"],
              date="2025-03", url="https://doi.org/10.1109/LRA.2025.3531153", doi="10.1109/LRA.2025.3531153",
              abstract="This study aims to develop a system that can support workers by utilizing robots that anyone can easily use and flexibly respond to various tasks. The system adopts a large language model for work planning and generates tasks that robots can execute by making bidirectional and interactive suggestions through natural language dialogue.",
              extra_fields={"publicationTitle": "IEEE Robotics and Automation Letters", "volume": "10",
                            "issue": "3", "pages": "2383-2390"},
              pdf=None))

P.append(dict(itype="preprint", cat="02 Robot Agent", tags=["LLM", "Agent"],
              title="ReAct: Synergizing Reasoning and Acting in Language Models",
              authors=["Shunyu Yao", "Jeffrey Zhao", "Dian Yu", "Nan Du", "Izhak Shafran", "Karthik Narasimhan", "Yuan Cao"],
              date="2022-10-06", url="https://arxiv.org/abs/2210.03629", archive="arXiv", archive_location="2210.03629",
              abstract="We explore the use of LLMs to generate both reasoning traces and task-specific actions in an interleaved manner, allowing for greater synergy between the two. ReAct overcomes prevalent issues of hallucination and error propagation in chain-of-thought reasoning by interacting with a simple Wikipedia API.",
              extra="会议：ICLR 2023",
              pdf="02_Robot_Agent/yao-2023-react-reasoning-acting.pdf"))

P.append(dict(itype="preprint", cat="02 Robot Agent", tags=["Agent", "Robot Planning", "Industrial Robot"],
              title="Do As I Can, Not As I Say: Grounding Language in Robotic Affordances",
              authors=["Michael Ahn", "Anthony Brohan", "Noah Brown", "Yevgen Chebotar", "Omar Cortes", "Byron David",
                       "Chelsea Finn", "Chuyuan Fu", "Keerthana Gopalakrishnan", "Karol Hausman", "Alex Herzog", "Daniel Ho"],
              date="2022-04-04", url="https://arxiv.org/abs/2204.01691", archive="arXiv", archive_location="2204.01691",
              abstract="Large language models can encode a wealth of semantic knowledge about the world, but they lack real-world experience. We propose to ground language in pretrained skills so that the model proposes natural language actions that are both feasible and contextually appropriate, with value functions providing the grounding to connect this knowledge to a particular physical environment.",
              extra="会议：CoRL 2022",
              pdf="02_Robot_Agent/ahn-2022-saycan-do-as-i-can.pdf"))

P.append(dict(itype="preprint", cat="02 Robot Agent", tags=["Agent", "Embodied AI"],
              title="Inner Monologue: Embodied Reasoning through Planning with Language Models",
              authors=["Wenlong Huang", "Fei Xia", "Ted Xiao", "Harris Chan", "Jacky Liang", "Pete Florence", "Andy Zeng",
                       "Jonathan Tompson", "Igor Mordatch", "Yevgen Chebotar", "Pierre Sermanet", "Noah Brown",
                       "Tomas Jackson", "Linda Luu", "Sergey Levine", "Karol Hausman", "Brian Ichter"],
              date="2022-07-12", url="https://arxiv.org/abs/2207.05608", archive="arXiv", archive_location="2207.05608",
              abstract="We investigate to what extent LLMs used in embodied contexts can reason over sources of feedback provided through natural language, without any additional training. Leveraging environment feedback, LLMs form an inner monologue that allows them to more richly process and plan in robotic control scenarios.",
              extra="会议：CoRL 2022",
              pdf="02_Robot_Agent/huang-2022-inner-monologue-embodied-reasoning.pdf"))

P.append(dict(itype="preprint", cat="03 RAG Knowledge", tags=["RAG"],
              title="Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
              authors=["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus", "Fabio Petroni", "Vladimir Karpukhin",
                       "Naman Goyal", "Heinrich Kuettler", "Mike Lewis", "Wen-tau Yih", "Tim Rocktaeschel",
                       "Sebastian Riedel", "Douwe Kiela"],
              date="2020-05-22", url="https://arxiv.org/abs/2005.11401", archive="arXiv", archive_location="2005.11401",
              abstract="We explore a general-purpose fine-tuning recipe for retrieval-augmented generation (RAG), models which combine pre-trained parametric and non-parametric memory for language generation. We compare two RAG formulations and set the state of the art on three open domain QA tasks.",
              extra="会议：NeurIPS 2020",
              pdf="03_RAG_Knowledge/lewis-2020-rag-retrieval-augmented-generation.pdf"))

P.append(dict(itype="preprint", cat="03 RAG Knowledge", tags=["LLM", "Agent"],
              title="ChatGPT for Robotics: Design Principles and Model Abilities",
              authors=["Sai Vemprala", "Rogerio Bonatti", "Arthur Bucker", "Ashish Kapoor"],
              date="2023-06-30", url="https://arxiv.org/abs/2306.17582", archive="arXiv", archive_location="2306.17582",
              abstract="This paper presents an experimental study regarding the use of OpenAI's ChatGPT for robotics applications. We outline a strategy that combines design principles for prompt engineering and the creation of a high-level function library which allows ChatGPT to adapt to different robotics tasks, simulators, and form factors.",
              extra="机构：Microsoft",
              pdf="03_RAG_Knowledge/vemprala-2023-chatgpt-for-robotics.pdf"))

P.append(dict(itype="preprint", cat="04 Robot Software Architecture", tags=["Software Architecture"],
              title="Software Architectures for Robotics Systems: A Systematic Mapping Study",
              authors=["Aakash Ahmad", "Muhammad Ali Babar"],
              date="2016-12", url="https://arxiv.org/abs/1701.05453", archive="arXiv", archive_location="1701.05453",
              abstract="We carried out a Systematic Mapping Study to identify and analyze the relevant literature based on 56 peer-reviewed papers, taxonomically classifying existing research and mapping solutions, frameworks, notations and evaluation methods to highlight the role of software architecture in robotic systems.",
              extra_fields={"publicationTitle": "Journal of Systems and Software", "volume": "122", "pages": "16-39"},
              pdf="04_Robot_Software_Architecture/ahmed-2016-software-architectures-robotics-mapping.pdf"))

P.append(dict(itype="book", cat="04 Robot Software Architecture", tags=["Software Architecture", "Missing-PDF"],
              title="ROS: The Complete Reference (Volume 1)",
              authors=["Aaron Martinez", "Enrique Fernandez"],
              date="2013", url="https://www.packtpub.com/", abstract="",
              extra="出版社：Packt Publishing；商业图书，暂无开放 PDF，替代阅读：ROS 2 官方文档 docs.ros.org",
              pdf=None))

P.append(dict(itype="preprint", cat="05 Embodied AI", tags=["Embodied AI"],
              title="Aligning Cyber Space with Physical World: A Comprehensive Survey on Embodied AI",
              authors=["Yang Liu", "Weixing Chen", "Yongjie Bai", "Xiaodan Liang", "Guanbin Li", "Wen Gao", "Liang Lin"],
              date="2024-07-09", url="https://arxiv.org/abs/2407.06886", archive="arXiv", archive_location="2407.06886",
              abstract="Embodied AI is crucial for achieving Artificial General Intelligence. We analyze four main research targets: embodied perception, embodied interaction, embodied agent, and sim-to-real adaptation, covering state-of-the-art methods, essential paradigms, and comprehensive datasets.",
              extra_fields={"publicationTitle": "IEEE/ASME Transactions on Mechatronics"},
              pdf="05_Embodied_AI/liu-2024-embodied-ai-survey.pdf"))

P.append(dict(itype="preprint", cat="05 Embodied AI", tags=["Embodied AI"],
              title="Foundation Models in Robotics: Applications, Challenges, and the Future",
              authors=["Roya Firoozi", "Johnathan Tucker", "Stephen Tian", "Anirudha Majumdar", "Jiankai Sun",
                       "Weiyu Liu", "Yuke Zhu", "Shuran Song", "Ashish Kapoor", "Karol Hausman", "Brian Ichter",
                       "Danny Driess", "Jiajun Wu", "Cewu Lu", "Mac Schwager"],
              date="2023-12-12", url="https://arxiv.org/abs/2312.07843", archive="arXiv", archive_location="2312.07843",
              abstract="We survey applications of pretrained foundation models in robotics, exploring how they contribute to improving robot capabilities in the domains of perception, decision-making, and control, and discussing the challenges hindering their adoption in robot autonomy.",
              pdf="05_Embodied_AI/firoozi-2023-foundation-models-robotics.pdf"))

items_by_cat = {}
for p in P:
    iid = add_item(p["itype"], p["title"], p["authors"], p["date"], p.get("url"),
                   p.get("doi"), p.get("abstract"), p.get("archive"), p.get("archive_location"),
                   p.get("extra"), p.get("extra_fields"))
    add_tags(iid, p["tags"])
    add_to_collections(iid, p["cat"])
    items_by_cat.setdefault(p["cat"], []).append(p["title"])
    if p.get("pdf"):
        add_attachment(iid, p["pdf"])

con.commit()
print("collections:", cur.execute("SELECT COUNT(*) FROM collections").fetchone()[0])
print("items:", cur.execute("SELECT COUNT(*) FROM items").fetchone()[0])
print("attachments:", cur.execute("SELECT COUNT(*) FROM itemAttachments").fetchone()[0])
print("tags:", cur.execute("SELECT COUNT(*) FROM tags").fetchone()[0])
print("itemTags:", cur.execute("SELECT COUNT(*) FROM itemTags").fetchone()[0])
print("collectionItems:", cur.execute("SELECT COUNT(*) FROM collectionItems").fetchone()[0])
con.close()
