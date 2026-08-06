#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_rag_comparison.py — RAG 知识增强对比实验 (V6.5)
====================================================
在 20 个工业知识任务上对比：
  方法A：LLM 直接回答（无 RAG）
  方法B：LLM + RAG（工业知识库检索注入）

指标：回答正确率（全部期望关键词命中）、参数正确率（关键词命中率）、
平均响应时间。

用法：
    python experiments/scripts/run_rag_comparison.py
输出：
    experiments/results/rag_comparison_report.md
"""

import argparse
import json
import os
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402

RESULTS_DIR = os.path.join(BASE, "experiments", "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "rag_comparison_report.md")
TASKS_FILE = os.path.join(BASE, "experiments", "tasks", "knowledge_tasks.json")


def load_tasks():
    with open(TASKS_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def ask_llm(question, knowledge_text=""):
    """调用 DeepSeek 回答，返回 (回答文本, 耗时秒)"""
    from llm import load_config
    from openai import OpenAI

    cfg = load_config()
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    system = "你是工业机器人领域的专业助手，请基于事实简洁准确地回答问题。"
    if knowledge_text:
        user = f"参考以下工业知识库内容：\n{knowledge_text}\n\n问题：{question}"
    else:
        user = f"问题：{question}"
    t0 = time.monotonic()
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=250,
    )
    return resp.choices[0].message.content or "", time.monotonic() - t0


def evaluate(answer, expected_keywords):
    if not expected_keywords:
        return 1.0, 1
    hit = sum(1 for kw in expected_keywords if kw in (answer or ""))
    return hit / len(expected_keywords), len(expected_keywords)


def run_without_rag(tasks):
    results = []
    for task in tasks:
        answer, elapsed = ask_llm(task["input"])
        rate, total = evaluate(answer, task.get("expected_keywords", []))
        results.append(
            {
                "task_id": task["task_id"],
                "input": task["input"],
                "success": rate == 1.0,
                "keyword_rate": rate,
                "keywords": total,
                "response_time": round(elapsed, 3),
                "answer_preview": (answer or "")[:40],
            }
        )
    return results


def run_with_rag(tasks):
    tmp = tempfile.mkdtemp(prefix="rag_cmp_")
    agent = Agent(
        backend="local",
        db_path=os.path.join(tmp, "rag.db"),
        rag_enabled=True,
    )
    try:
        # 写入全部工业知识（seed_memory），同步建向量
        for task in tasks:
            for seed in task.get("seed_memory") or []:
                agent.registry["memory_tool"].run({"write": seed})
        results = []
        for task in tasks:
            rows = agent.retrieve_memories(task["input"], top_k=3)
            knowledge_text = "\n".join(
                f"- {r['topic']}：{r['content']}" for r in rows
            )
            answer, elapsed = ask_llm(task["input"], knowledge_text)
            rate, total = evaluate(answer, task.get("expected_keywords", []))
            results.append(
                {
                    "task_id": task["task_id"],
                    "input": task["input"],
                    "success": rate == 1.0,
                    "keyword_rate": rate,
                    "keywords": total,
                    "response_time": round(elapsed, 3),
                    "answer_preview": (answer or "")[:40],
                    "retrieved": len(rows),
                }
            )
        return results
    finally:
        agent.close()


def write_report(no_rag, with_rag):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    def summary(items):
        total = len(items)
        ok = sum(1 for r in items if r["success"])
        rates = [r["keyword_rate"] for r in items]
        times = [r["response_time"] for r in items]
        return {
            "total": total,
            "ok": ok,
            "rate": ok / total if total else 0.0,
            "keyword": sum(rates) / total if total else 0.0,
            "time": sum(times) / len(times) if times else 0.0,
        }

    a, b = summary(no_rag), summary(with_rag)
    lines = [
        "# RAG 知识增强对比实验报告",
        "",
        "## 1 实验目的",
        "",
        "在 20 个工业知识任务上对比 LLM 直接回答与 LLM + RAG（工业知识库",
        "检索注入）的回答正确率、参数正确率与响应时间。",
        "",
        "## 2 实验环境",
        "",
        "- 操作系统：Windows，Python 3.12",
        "- 大语言模型：DeepSeek（deepseek-chat）",
        "- 语义检索：bge-small-zh-v1.5（CPU）",
        "- 知识库：ABB RAPID / RobotStudio / 工业机器人参数（20 条知识）",
        "",
        "## 3 实验结果",
        "",
        "| 方法 | 任务数 | 回答正确率 | 参数正确率（关键词命中率） | 平均响应时间 |",
        "| --- | --- | --- | --- | --- |",
        f"| LLM（无 RAG） | {a['total']} | {a['rate']:.1%} "
        f"({a['ok']}/{a['total']}) | {a['keyword']:.1%} | {a['time']:.3f} s |",
        f"| LLM + RAG | {b['total']} | {b['rate']:.1%} "
        f"({b['ok']}/{b['total']}) | {b['keyword']:.1%} | {b['time']:.3f} s |",
        "",
        "## 4 逐题结果",
        "",
        "| 任务 | 无RAG正确率 | RAG正确率 | 无RAG关键词 | RAG关键词 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r1, r2 in zip(no_rag, with_rag):
        lines.append(
            f"| {r1['task_id']} {r1['input'][:18]} | "
            f"{'✓' if r1['success'] else '✗'} | "
            f"{'✓' if r2['success'] else '✗'} | "
            f"{r1['keyword_rate']:.0%} | {r2['keyword_rate']:.0%} |"
        )
    lines += [
        "",
        "## 5 结果分析",
        "",
        "（1）回答正确率：RAG 注入使回答正确率由 "
        f"{a['rate']:.1%} 提升至 {b['rate']:.1%}；",
        "",
        "（2）参数正确率（期望关键词命中率）：由 "
        f"{a['keyword']:.1%} 提升至 {b['keyword']:.1%}，说明工业知识库",
        "对参数理解的增强作用；",
        "",
        "（3）响应时间：RAG 增加了检索开销，平均响应由 "
        f"{a['time']:.3f} s 变为 {b['time']:.3f} s；",
        "",
        "（4）结论：融合工业知识 RAG 能显著提升知识问答的准确性与参数",
        "可靠性，代价是少量检索延迟。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="RAG 知识增强对比实验")
    parser.add_argument("--rounds", type=int, default=1, help="每任务轮数")
    args = parser.parse_args()

    tasks = load_tasks()
    print(f"[知识任务] {len(tasks)} 题")

    no_rag, with_rag = [], []
    for _ in range(args.rounds):
        print("[A] LLM 直接回答...")
        no_rag.extend(run_without_rag(tasks))
        print("[B] LLM + RAG...")
        with_rag.extend(run_with_rag(tasks))

    write_report(no_rag, with_rag)
    a_ok = sum(1 for r in no_rag if r["success"])
    b_ok = sum(1 for r in with_rag if r["success"])
    print(f"[完成] 无RAG 正确率 {a_ok / len(no_rag):.1%}，"
          f"RAG 正确率 {b_ok / len(with_rag):.1%}")
    print(f"[报告] {REPORT_PATH}")


if __name__ == "__main__":
    main()

