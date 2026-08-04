#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_task_sets.py — 论文任务集批量运行与评测 (V6.2)
==================================================
按 experiments/tasks/ 下三类任务集批量运行并评测：

  1. basic_tasks.json    基础运动/状态任务
     - 链路：Agent(backend=robotstudio) -> robot_tool -> RobotStudioBackend
     - 评测：execution_success（期望工具/动作匹配 + 全部步骤成功）
  2. complex_tasks.json  复杂规划任务
     - 评测：plan_and_execution（子任务数量 + 期望工具 + 执行成功）
              / recall_and_execution（记忆召回 + 动作 + 执行）
  3. knowledge_tasks.json 工业知识任务（RAG 问答）
     - 检索：Agent RAG（retrieve_memories，语义/关键词）
     - 生成：DeepSeek（llm.py 配置）
     - 评测：answer_and_citation（回答关键词命中 + 是否引用知识库）

用法：
    python experiments/scripts/run_task_sets.py --tasks all --backend mock --rounds 3
    python experiments/scripts/run_task_sets.py --tasks basic --backend real --rounds 5
    python experiments/scripts/run_task_sets.py --tasks knowledge --rounds 5   # 需 DeepSeek Key

输出：experiments/results/task_sets_{basic,complex,knowledge}.csv
同时写入统一实验日志（runtime_logs.json，task_type 分类）。
"""

import argparse
import csv
import datetime
import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.planner import MockPlanPlanner  # noqa: E402
from experiments.tasklog.task_logger import TaskLogger  # noqa: E402
from mock_robotstudio_planner import RobotStudioMockPlanner  # noqa: E402

TASKS_DIR = os.path.join(BASE, "experiments", "tasks")
RESULTS_DIR = os.path.join(BASE, "experiments", "results")


def load_tasks(name):
    path = os.path.join(TASKS_DIR, f"{name}_tasks.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def collect_seeds(tasks):
    """收集所有预置记忆（兼容 memory / seed_memory，dict 或 list）"""
    seeds = []
    for t in tasks:
        seed = t.get("seed_memory") or t.get("memory")
        if isinstance(seed, list):
            seeds.extend(seed)
        elif seed:
            seeds.append(seed)
    return seeds


def make_db(seeds):
    tmp = tempfile.mkdtemp(prefix="task_sets_")
    db_path = os.path.join(tmp, "eval.db")
    if seeds:
        sa = Agent(backend="local", db_path=db_path, planner=MockPlanPlanner())
        try:
            for seed in seeds:
                sa.registry["memory_tool"].run({"write": seed})
        finally:
            sa.close()
    return db_path


def build_agent(backend, planner, db_path, real=False):
    """构造评测 Agent（basic/complex 用 robotstudio 后端）"""
    if backend == "real":
        from robotstudio.robotstudio_client import RobotStudioClient

        client = RobotStudioClient(
            host="127.0.0.1", port=30000, timeout_seconds=20.0, mock=False
        )
        return Agent(
            backend="robotstudio",
            db_path=db_path,
            planner=planner,
            robotstudio_client=client,
        )
    return Agent(backend="robotstudio", db_path=db_path, planner=planner)


def check_basic_complex(task, resp, agent):
    """按 evaluation 字段评测基础/复杂任务，返回 (ok, reason)"""
    plan = resp["plan"]
    steps = plan.get("steps", [])
    if not steps:
        return False, "计划为空"
    tools = {s.get("tool") for s in steps}

    exp = task.get("expected") or {}
    if exp.get("tool") and exp["tool"] not in tools:
        return False, f"工具不匹配: 期望 {exp['tool']}"
    if exp.get("action"):
        matched = any(s.get("args", {}).get("action") == exp["action"] for s in steps)
        if not matched:
            return False, f"动作不匹配: 期望 {exp['action']}"
    if task.get("expected_tools") and not (set(task["expected_tools"]) & tools):
        return False, "期望工具未出现"
    if task.get("min_steps") and len(steps) < task["min_steps"]:
        return False, f"步骤数不足: {len(steps)} < {task['min_steps']}"
    if task.get("expected_recall"):
        rows = agent.retrieve_memories(task["input"], top_k=3)
        if not any(task["expected_recall"] in r["topic"] for r in rows):
            return False, "记忆召回失败"
    for r in resp["step_results"]:
        if not r.get("ok"):
            return False, f"执行失败: {r.get('tool')}: {r.get('message')}"
    return True, ""


def run_basic_complex(name, tasks, backend, planner_name, rounds):
    """运行基础/复杂任务集"""
    seeds = collect_seeds(tasks)
    db_path = make_db(seeds)
    planner = RobotStudioMockPlanner() if planner_name == "robotstudio" else None

    rows = []
    for task in tasks:
        succ, totals, plans, execs, reasons = [], [], [], [], []
        for _ in range(rounds):
            agent = build_agent(backend, planner, db_path)
            try:
                resp = agent.handle(task["input"], task_type=task["task_type"])
                ok, reason = check_basic_complex(task, resp, agent)
            except Exception as exc:
                ok, reason = False, f"异常: {exc}"
            finally:
                agent.close()
            timings = agent.last_timings
            totals.append(timings["total_seconds"])
            plans.append(timings["plan_seconds"])
            execs.append(timings["exec_seconds"])
            succ.append(1 if ok else 0)
            if not ok:
                reasons.append(reason)
        rows.append(
            {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "input": task["input"],
                "evaluation": task.get("evaluation", ""),
                "rounds": rounds,
                "success_rate": round(sum(succ) / rounds, 4),
                "avg_response_s": round(sum(totals) / rounds, 4),
                "avg_plan_s": round(sum(plans) / rounds, 4),
                "avg_exec_s": round(sum(execs) / rounds, 4),
                "failures": "; ".join(sorted(set(reasons))[:2]),
            }
        )
        print(
            f"  [{task['task_id']}] 成功率={rows[-1]['success_rate']:.0%} "
            f"响应={rows[-1]['avg_response_s']}s"
            + (f" 失败: {rows[-1]['failures']}" if rows[-1]["failures"] else "")
        )
    write_csv(os.path.join(RESULTS_DIR, f"task_sets_{name}.csv"), rows)
    return rows


def ask_llm(question, context, cfg):
    """调用 DeepSeek 生成答案（context 为空表示无 RAG）"""
    from openai import OpenAI

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    system = "你是工业机器人知识助手，请用中文简洁回答。"
    if context:
        system += "\n请优先依据以下知识库内容回答：\n" + context
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
        max_tokens=300,
    )
    return resp.choices[0].message.content or ""


def run_knowledge(tasks, rounds):
    """RAG 问答评测：无RAG vs RAG 的回答正确性与知识引用"""
    from llm import load_config

    cfg = load_config()
    if not (cfg.get("api_key", "") or "").startswith("sk-"):
        print("[knowledge] 无 DeepSeek Key，跳过知识问答评测（需 .env 配置）")
        return []

    seeds = collect_seeds(tasks)
    db_path = make_db(seeds)
    logger = TaskLogger()
    # 检索 Agent 全局复用（避免每轮重复加载嵌入模型）
    retriever_agent = Agent(
        backend="local",
        db_path=db_path,
        planner=MockPlanPlanner(),
        rag_enabled=True,
    )
    rows = []
    try:
        for task in tasks:
            rec = {
                "task_id": task["task_id"],
                "task_type": "knowledge",
                "input": task["input"],
                "evaluation": task.get("evaluation", ""),
                "rounds": rounds,
            }
            for mode in ("no_rag", "rag"):
                hits_total, ok_total, cited_total = 0, 0, 0
                times = []
                for _ in range(rounds):
                    try:
                        t0 = datetime.datetime.now()
                        question = task["input"]
                        context = ""
                        cited = False
                        if mode == "rag":
                            rows_r = retriever_agent.retrieve_memories(question, top_k=3)
                            context = "\n".join(
                                f"- {r['topic']}：{r['content']}（{r['source']}）"
                                for r in rows_r
                            )
                            cited = any(
                                seed["topic"] in r["topic"]
                                for seed in seeds
                                for r in rows_r
                                if isinstance(seed, dict)
                            )
                        answer = ask_llm(question, context, cfg)
                        hits = sum(
                            1 for kw in task.get("expected_keywords", []) if kw in answer
                        )
                        ok = hits > 0
                        dt = (datetime.datetime.now() - t0).total_seconds()
                        times.append(dt)
                        hits_total += hits
                        ok_total += 1 if ok else 0
                        cited_total += 1 if cited else 0
                        logger.log(
                            task_type="knowledge",
                            input=question,
                            agent_enabled=False,
                            rag_enabled=(mode == "rag"),
                            generated_plan={"mode": mode, "answer": answer[:80]},
                            success=ok,
                            error="" if ok else "关键词未命中",
                            response_time=round(dt, 4),
                        )
                    except Exception as exc:
                        times.append(0.0)
                        logger.log(
                            task_type="knowledge",
                            input=task["input"],
                            agent_enabled=False,
                            rag_enabled=(mode == "rag"),
                            success=False,
                            error=f"知识问答异常: {exc}",
                            response_time=0.0,
                        )
                n = max(rounds, 1)
                rec[f"{mode}_answer_ok_rate"] = round(ok_total / n, 4)
                rec[f"{mode}_keyword_hits_avg"] = round(hits_total / n, 2)
                rec[f"{mode}_cited_rate"] = round(cited_total / n, 4)
                rec[f"{mode}_avg_s"] = round(sum(times) / n, 4)
            rows.append(rec)
            print(
                f"  [{task['task_id']}] 无RAG 命中={rec['no_rag_keyword_hits_avg']} "
                f"RAG 命中={rec['rag_keyword_hits_avg']} "
                f"引用率={rec['rag_cited_rate']:.0%}"
            )
    finally:
        retriever_agent.close()
    write_csv(os.path.join(RESULTS_DIR, "task_sets_knowledge.csv"), rows)
    return rows


def write_csv(path, rows):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[结果] CSV 已保存: {path}")


def main():
    parser = argparse.ArgumentParser(description="论文任务集批量运行与评测")
    parser.add_argument("--tasks", default="all",
                        choices=["all", "basic", "complex", "knowledge"])
    parser.add_argument("--backend", default="mock", choices=["mock", "real"])
    parser.add_argument("--planner", default="robotstudio",
                        choices=["robotstudio", "deepseek"])
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"[任务集] tasks={args.tasks} backend={args.backend} "
          f"planner={args.planner} rounds={args.rounds}")

    if args.tasks in ("all", "basic"):
        print("[基础运动]")
        run_basic_complex("basic", load_tasks("basic"), args.backend,
                          args.planner, args.rounds)
    if args.tasks in ("all", "complex"):
        print("[复杂规划]")
        run_basic_complex("complex", load_tasks("complex"), args.backend,
                          args.planner, args.rounds)
    if args.tasks in ("all", "knowledge"):
        print("[工业知识 RAG 问答]")
        run_knowledge(load_tasks("knowledge"), args.rounds)
    print("[任务集] 完成")


if __name__ == "__main__":
    main()
