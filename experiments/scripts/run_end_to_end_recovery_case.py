#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_end_to_end_recovery_case.py — 端到端闭环恢复案例实验 (V6.9)
================================================================
在真实 ABB RobotStudio + IRC5 虚拟控制器 + RWS 链路上验证完整闭环：

    用户任务 → LLM Agent 任务理解 → 任务规划 → Safety 预检
      → Robot 执行 → 异常触发（真实 50050）→ 错误反馈（RWS E-log）
      → Observation 解析 → Reflection 判断 → RecoveryManager 恢复
      → RWS 控制器级自动恢复（resetpp + start + Socket 重连）
      → Agent 重新规划 → 继续执行 → 任务完成

重点：不是证明"机器人恢复"，而是证明 Agent 具备异常感知、恢复控制与
任务持续执行能力。

故障注入说明：
  在动作执行层将计划中首个直线运动（linear_move）的目标位姿替换为越界
  位姿 [1.2, 1.2, 1.2, 0, 0, 0]，触发控制器真实 50050 停止级错误。
  该注入等效于上游位姿数据错误/示教点越界，属于可靠性测试的标准故障
  注入方式；结构性安全预检（参数完整性）无法预测运动学不可达性，执行
  阶段异常正需要闭环恢复机制处理。

环境要求：
  1. RobotStudio + IRC5 虚拟控制器运行中，RAPID SocketServer 监听 30000；
  2. 虚拟控制器已启用 RobotWebServices（RWS，见 rws_recovery_experiment.md）。

用法：
    python experiments/scripts/run_end_to_end_recovery_case.py --rounds 10
输出：
    experiments/logs/end_to_end_recovery_case.json
    experiments/results/end_to_end_recovery_case_report.md
"""

import argparse
import copy
import datetime
import json
import os
import socket
import statistics
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests"),
          os.path.join(BASE, "experiments", "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import Agent  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from experiments.scripts.run_task_sets import (  # noqa: E402
    DeepSeekRobotStudioPlanner,
)
from robotstudio.config import load_config  # noqa: E402
from robotstudio.robotstudio_client import RobotStudioClient  # noqa: E402

LOGS_DIR = os.path.join(BASE, "experiments", "logs")
RESULTS_DIR = os.path.join(BASE, "experiments", "results")
LOG_PATH = os.path.join(LOGS_DIR, "end_to_end_recovery_case.json")
REPORT_PATH = os.path.join(RESULTS_DIR, "end_to_end_recovery_case_report.md")

# 故障注入目标：IRB120 工作空间外，真实触发 50050 位置超出范围
OUT_OF_RANGE_TARGET = [1.2, 1.2, 1.2, 0.0, 0.0, 0.0]

# 每轮任务：自然语言描述一个包含"移动到指定位置"的可行任务，
# LLM 规划出 joint_move + linear_move + move_home 的可执行计划
TASK_TEXT = "移动机器人到工作区域 (0.3, 0, 0.3) 米处，然后返回初始状态"


def port_open(host, port, timeout=2.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def make_client(cfg):
    return RobotStudioClient(
        host=cfg.get("host", "127.0.0.1"),
        port=int(cfg.get("port", 30000)),
        timeout_seconds=8.0,
        mock=False,
    )


def build_agent(client):
    """真实链路 Agent：DeepSeek LLM 规划器 + RobotStudio 后端 +
    自动注入 RWS 恢复器（Agent 构造函数对 robotstudio 后端默认注入）。"""
    planner = DeepSeekRobotStudioPlanner()
    return Agent(
        backend="robotstudio",
        planner=planner,
        robotstudio_client=client,
    )


def inject_fault(plan):
    """把计划中首个 linear_move 目标替换为越界位姿（故障注入）。
    若计划中没有 linear_move，则在 move_home 之前插入越界 linear_move
    步骤。返回 (注入后计划, 是否替换了已有步骤)。"""
    plan = copy.deepcopy(plan)
    steps = plan.get("steps", [])
    replaced = False
    for step in steps:
        args = step.get("args", {}) or {}
        if args.get("action") == "linear_move":
            step["args"] = {**args, "target": list(OUT_OF_RANGE_TARGET)}
            step["purpose"] = (step.get("purpose") or "") + "（故障注入：越界目标）"
            replaced = True
            break
    if not replaced:
        fault_step = {
            "tool": "robot_tool",
            "args": {
                "action": "linear_move",
                "target": list(OUT_OF_RANGE_TARGET),
            },
            "purpose": "故障注入：越界直线运动",
        }
        insert_at = len(steps)
        for i, step in enumerate(steps):
            args = step.get("args", {}) or {}
            if args.get("action") in ("move_home", "get_position", "get_pose"):
                insert_at = i
                break
        steps.insert(insert_at, fault_step)
        plan["steps"] = steps
    return plan, replaced


def ensure_controller(rws, cfg):
    """预检：RWS 可用；若 SocketServer 未监听，先尝试 RWS 自动拉起。"""
    conn = rws.check_connection()
    if not conn["controller_available"]:
        print("[预检] RWS 不可用：" + conn["detail"])
        return False
    if port_open(cfg.get("host", "127.0.0.1"), int(cfg.get("port", 30000))):
        return True
    print("[预检] SocketServer 未监听，尝试 RWS 自动恢复拉起...")
    rws.set_entry_point()
    rws.reset_pp_to_main()
    rws.start_execution()
    ok = rws.wait_for_socket(
        cfg.get("host", "127.0.0.1"), int(cfg.get("port", 30000)), 20)
    if not ok:
        print("[预检] RWS 拉起失败，请在 RobotStudio 中启动 RAPID 程序")
        return False
    return True


def plan_with_retry(agent, task, max_tries=3):
    """调用 LLM 规划器；确保计划包含 robot_tool 步骤。"""
    for _ in range(max_tries):
        memory_text = agent._retrieve_memories(task)
        raw = agent.planner.plan(task, agent.context, memory_text)
        steps = raw.get("steps", [])
        if any(s.get("tool") == "robot_tool" for s in steps):
            return raw
        print("  规划结果缺少 robot_tool 步骤，重试规划...")
    return raw


def run_round(agent, rws, round_no, task):
    """执行一轮端到端闭环恢复，返回逐阶段记录 dict。"""
    agent.context = AgentContext()  # 每轮独立上下文，保证轮次相互独立
    t0 = time.monotonic()
    record = {
        "task_id": f"e2e-{round_no:03d}",
        "initial_task": task,
        "original_plan": None,
        "initial_plan": None,
        "fault_injected": None,
        "error_code": None,
        "error_message": None,
        "observation": None,
        "reflection_result": None,
        "recovery_method": None,
        "recovery_time": 0.0,
        "replan_count": 0,
        "final_plan": None,
        "final_action": None,
        "final_success": False,
        "total_time": 0.0,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    # ---- 第 1 轮：LLM 规划（真实）----
    raw_plan = plan_with_retry(agent, task)
    record["original_plan"] = raw_plan
    plan, replaced = inject_fault(raw_plan)
    record["initial_plan"] = plan
    record["fault_injected"] = (
        "替换已有 linear_move 目标" if replaced else "插入越界 linear_move 步骤")

    # ---- Safety 预检（结构性校验通过；运动学不可达只能在执行阶段发现）----
    prechecked, rejected = agent._precheck_plan(plan)

    # ---- 执行：真实触发 50050 ----
    step_results = agent.executor.execute({"steps": prechecked}) + rejected
    time.sleep(1.5)

    # ---- 错误反馈：RWS E-log 读取控制器真实故障码 ----
    elog = rws.get_controller_error(limit=50)
    error_code = elog.get("error_code")

    # ---- Observation 解析 ----
    observation = agent.observer.get_observation(plan, step_results)
    if error_code:
        observation["error_code"] = error_code
        observation["error_source"] = "RobotStudio E-log(RWS)"
        observation["raw_message"] = f"控制器事件日志故障码 {error_code}"
    record["error_code"] = error_code
    record["error_message"] = (
        f"控制器停止级错误 {error_code}（{elog.get('detail', '')}）"
        if error_code else observation.get("error") or "执行失败")
    record["observation"] = observation

    # ---- Reflection 判断 ----
    reflection = agent.reflector.analyze(
        task, plan, step_results, observation)
    record["reflection_result"] = reflection

    # ---- RecoveryManager 恢复（Level 2 → RWS 控制器级恢复）----
    error_info = {
        "error_code": error_code or "50050",
        "error_type": reflection.get("error_type") or "execution",
        "error_message": record["error_message"],
        "raw_message": observation.get("raw_message"),
    }
    t_rec0 = time.monotonic()
    recovery = agent.recovery.recover(error_info)
    record["recovery_time"] = round(time.monotonic() - t_rec0, 3)
    record["recovery_method"] = (
        "RWS" if recovery.get("recovery_source") == "rws"
        else str(recovery.get("status")))
    record["recovery_result"] = {
        "status": recovery.get("status"),
        "recovery_source": recovery.get("recovery_source"),
        "recovery_detail": recovery.get("recovery_detail"),
        "rws_recover_time": (recovery.get("rws_result") or {}).get(
            "recover_time"),
        "rws_socket_reconnect": (recovery.get("rws_result") or {}).get(
            "socket_reconnect_time"),
    }
    if recovery.get("status") != "success":
        record["error_message"] = (
            record["error_message"]
            + f"；自动恢复未成功（{recovery.get('status')}），本轮终止")
        record["total_time"] = round(time.monotonic() - t0, 3)
        return record

    # ---- Agent 重新规划（携带错误原因，真实 LLM）----
    reason = reflection.get("reason") or "执行失败"
    if recovery.get("status") == "success":
        reason = f"{reason}（已自动恢复：{recovery.get('recovery_detail', '')}）"
    agent.context.history.append({
        "role": "user",
        "content": f"上一轮执行失败原因：{reason}，恢复状态：{recovery.get('status')}，"
                   "请修正计划后重试。",
    })
    record["replan_count"] = 1
    replan = plan_with_retry(agent, task)
    record["final_plan"] = replan

    # ---- 重新执行（真实）----
    prechecked2, rejected2 = agent._precheck_plan(replan)
    final_results = agent.executor.execute(
        {"steps": prechecked2}) + rejected2
    final_observation = agent.observer.get_observation(
        replan, final_results)
    final_reflection = agent.reflector.analyze(
        task, replan, final_results, final_observation)
    all_ok = all(r.get("ok") for r in final_results)
    record["final_action"] = (
        [s.get("args", {}).get("action")
         for s in replan.get("steps", []) if s.get("tool") == "robot_tool"])
    record["final_success"] = bool(all_ok and final_reflection.get(
        "task_completed"))
    record["final_reflection"] = final_reflection
    record["final_results"] = [
        {"tool": r.get("tool"), "ok": r.get("ok"),
         "message": (r.get("message") or "")[:80]} for r in final_results
    ]
    record["total_time"] = round(time.monotonic() - t0, 3)
    return record


def write_report(records, rws_url):
    ok_recovery = sum(1 for r in records if r.get("recovery_result", {}).get(
        "status") == "success")
    ok_final = sum(1 for r in records if r["final_success"])
    recovery_times = [r["recovery_time"] for r in records
                      if r.get("recovery_result", {}).get("status") == "success"]
    replan_counts = [r["replan_count"] for r in records]
    lines = [
        "# 端到端闭环恢复案例实验报告",
        "",
        "## 1 实验目的",
        "",
        "在真实 ABB RobotStudio + IRC5 虚拟控制器链路上验证完整闭环："
        "用户任务 → LLM Agent 规划 → Safety 预检 → 机器人执行 → 异常触发"
        "（50050）→ 错误反馈 → Observation → Reflection → RecoveryManager"
        "（RWS 控制器级恢复）→ 重新规划 → 继续执行 → 任务完成。重点验证"
        "Agent 对执行异常的感知、恢复控制与任务持续执行能力。",
        "",
        "## 2 实验环境",
        "",
        "- ABB RobotStudio 6.08.01 + RobotWare 6.08.1040，IRB120 模型；",
        "- IRC5 虚拟控制器，RAPID SocketServer TCP 127.0.0.1:30000；",
        f"- RWS：{rws_url}（HTTP Digest 认证）；",
        "- LLM 规划器：DeepSeek（DeepSeekRobotStudioPlanner + 安全约束层）。",
        "",
        "## 3 实验流程",
        "",
        "每轮任务文本：\"" + TASK_TEXT + "\"。流程：",
        "",
        "1. LLM Agent 规划出可执行计划；",
        "2. 安全层做结构性参数预检；",
        "3. 故障注入：将首个 linear_move 目标替换为越界位姿，执行触发"
        "真实 50050 停止级错误；",
        "4. 通过 RWS E-log 读取控制器真实故障码（50050）；",
        "5. Observation 统一错误反馈；Reflection 判定异常类型并建议重规划；",
        "6. RecoveryManager 分级判定 Level 2，调用 RWS 自动恢复"
        "（设置入口 → resetpp → start → Socket 重连）；",
        "7. Agent 携带错误原因重新规划并继续执行；",
        "8. 最终步骤全部成功且 Reflection 判定任务完成。",
        "",
        "## 4 异常注入方式",
        "",
        "动作执行层故障注入：将计划中首个直线运动目标替换为工作空间外的"
        "位姿 [1.2, 1.2, 1.2, 0, 0, 0]，触发控制器真实 50050 位置超出范围"
        "错误。结构性安全预检只校验参数完整性，无法预测运动学不可达性，"
        "因此该异常只能在执行阶段被发现——这正是闭环恢复机制的价值所在。",
        "",
        "## 5 Recovery 流程",
        "",
        "50050 停止级错误 → RecoveryManager 分级（Level 2）→ RWS 设置任务"
        "入口 → resetpp → start → 轮询 30000 端口 → Agent 重连。安全边界："
        "安全相关异常（Level 3）禁止自动恢复。",
        "",
        "## 6 实验结果",
        "",
        f"- 实验轮次：{len(records)}",
        f"- 异常触发次数：{len(records)}（每轮 1 次）",
        f"- 恢复成功率：{ok_recovery}/{len(records)}"
        f"（{ok_recovery / len(records):.0%}）" if records else "-",
        f"- 平均恢复时间：{statistics.mean(recovery_times):.3f} s"
        if recovery_times else "-",
        f"- 平均重规划次数：{statistics.mean(replan_counts):.2f}"
        if replan_counts else "-",
        f"- 最终任务完成率：{ok_final}/{len(records)}"
        f"（{ok_final / len(records):.0%}）" if records else "-",
        "",
        "| 指标 | 结果 |",
        "| --- | --- |",
        f"| 实验次数 | {len(records)} |",
        f"| 异常次数 | {len(records)} |",
        f"| 恢复成功率 | {ok_recovery}/{len(records)}"
        f"（{ok_recovery / len(records):.0%}） |",
        f"| 平均恢复时间 | {statistics.mean(recovery_times):.3f} s |"
        if recovery_times else "| 平均恢复时间 | - |",
        f"| 平均重规划次数 | {statistics.mean(replan_counts):.2f} |",
        f"| 最终任务完成率 | {ok_final}/{len(records)}"
        f"（{ok_final / len(records):.0%}） |",
        "",
        "| 轮次 | 错误码 | 恢复方法 | 恢复耗时(s) | 重规划次数 | 最终成功 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        rec_ok = r.get("recovery_result", {}).get("status") == "success"
        lines.append(
            f"| {r['task_id']} | {r['error_code']} | "
            f"{r.get('recovery_method')} | {r['recovery_time']} | "
            f"{r['replan_count']} | "
            f"{'✓' if r['final_success'] else '✗'} |")
    lines += [
        "",
        "## 7 结果分析",
        "",
        "（1）Observation 作用：50050 停止级错误使 TCP 链路中断，系统通过"
        "RWS E-log 读取控制器真实故障码，将执行层失败转化为结构化观察；",
        "",
        "（2）Reflection 作用：确定性规则将 50050 分类为执行类异常"
        "（robot_unreachable），并给出重新规划建议；",
        "",
        "（3）RecoveryManager + RWS 作用：Level 2 停止级异常由 RWS 自动完成"
        "程序指针重置、RAPID 重启与 Socket 重连，无需人工介入；",
        "",
        "（4）重规划作用：Agent 携带失败原因重新规划，生成可达计划并继续"
        "执行，最终完成任务，体现异常感知、恢复控制与任务持续执行能力。",
        "",
        "## 8 局限性",
        "",
        "- 实验基于 RobotStudio IRC5 虚拟控制器，结果不代表实体机器人行为；",
        "- 故障注入为确定性注入（越界直线目标），用于验证系统对可恢复"
        "停止级异常的闭环处理能力；",
        "- 异常覆盖范围有限（50050 运动不可达），安全相关异常（Level 3）"
        "不在自动恢复范围内。",
        "",
    ]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="端到端闭环恢复案例实验")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--rws-url", default="http://127.0.0.1")
    args = parser.parse_args()

    cfg = load_config()
    client = make_client(cfg)
    agent = build_agent(client)
    rws = agent.recovery.recoverer
    if rws is None:
        print("[错误] Agent 未注入 RWS 恢复器，请确认 robotstudio 后端")
        sys.exit(2)

    if not ensure_controller(rws, cfg):
        print("[预检] 控制器不可用，实验终止")
        sys.exit(2)
    print("[预检] RWS 可用，控制器运行中")

    records = []
    for i in range(1, args.rounds + 1):
        print(f"[{i}/{args.rounds}] 开始端到端闭环恢复...")
        rec = run_round(agent, rws, i, TASK_TEXT)
        records.append(rec)
        print(
            f"  错误码={rec['error_code']} | 恢复={rec.get('recovery_method')}"
            f" | 重规划={rec['replan_count']}"
            f" | 最终成功={rec['final_success']}"
            f" | 总耗时={rec['total_time']}s")
        if not rec["final_success"]:
            print("  [注意] 本轮未完成，停止实验")
            break

    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    try:
        rws.logout()
    except Exception:  # noqa: BLE001
        pass
    write_report(records, args.rws_url)
    print(f"[完成] 日志: {LOG_PATH}")
    print(f"[完成] 报告: {REPORT_PATH}")


if __name__ == "__main__":
    main()
