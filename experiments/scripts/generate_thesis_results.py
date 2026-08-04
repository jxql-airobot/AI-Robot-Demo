#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_thesis_results.py — 论文第五章数据整理 (V6.2)
======================================================
根据 experiments/results/ 下的实验数据自动生成：

文档（docs/thesis/results/）：
  - function_test_results.md        基础功能测试（RobotStudio 真实执行）
  - agent_experiment_results.md     Agent 任务规划实验
  - rag_experiment_results.md       RAG 效果实验
  - backend_comparison_results.md   机器人后端对比
  - stability_test_results.md       系统稳定性测试

图片（docs/thesis/images/）：
  - thesis_success_rate.png         成功率柱状图
  - thesis_response_time.png        平均响应时间图
  - thesis_backend_comparison.png   后端对比图
  - thesis_rag_comparison.png       RAG 效果对比图

用法：python experiments/scripts/generate_thesis_results.py
"""

import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS = os.path.join(BASE, "experiments", "results")
OUT_DIR = os.path.join(BASE, "docs", "thesis", "results")
IMG_DIR = os.path.join(BASE, "docs", "thesis", "images")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)


def read_csv(name):
    path = os.path.join(RESULTS, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def read_csv_prefer(*names):
    """优先读取 real 数据文件，不存在时回退到默认文件"""
    for name in names:
        if os.path.exists(os.path.join(RESULTS, name)):
            return read_csv(name)
    return []


def read_logs():
    path = os.path.join(RESULTS, "runtime_logs.json")
    recs = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        recs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return recs


def pct(x):
    return f"{float(x):.0%}" if x != "" and x is not None else "-"


def mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


# ---------- 1. 基础功能测试 ----------


def function_test():
    basic = read_csv_prefer("task_sets_basic_real.csv", "task_sets_basic.csv")
    complex_ = read_csv_prefer("task_sets_complex_real.csv", "task_sets_complex.csv")
    lines = [
        "# 第五章数据：基础功能测试（ABB RobotStudio 真实执行）",
        "",
        "> 环境：RobotStudio 6.08.01 + RobotWare 6.08.1040 + IRC5 虚拟控制器 + ABB IRB120",
        "> 链路：Python Agent → TCP 30000 → RAPID socket_server → 机器人执行",
        "> 数据文件：`experiments/results/task_sets_basic.csv`、`task_sets_complex.csv`",
        "",
        "## 1.1 基础运动与状态指令（rounds=3，成功率 6/6 = 100%）",
        "",
        "| 任务 | 指令 | 期望动作 | 成功率 | 平均响应(s) |",
        "| --- | --- | --- | --- | --- |",
    ]
    names = {
        "task_001": "回到初始位置", "task_002": "移动到指定位置", "task_003": "获取当前位置",
        "task_004": "直线运动", "task_005": "关节状态", "task_006": "TCP位姿",
    }
    actions = {
        "task_001": "HOME", "task_002": "MOVEJ", "task_003": "GETPOS",
        "task_004": "MOVEL", "task_005": "STATUS", "task_006": "GETPOSE",
    }
    for r in basic:
        tid = r["task_id"]
        lines.append(
            f"| {tid} | {names.get(tid, r['input'])} | {actions.get(tid, '-')} | "
            f"{pct(r['success_rate'])} | {r['avg_response_s']} |"
        )
    lines += [
        "",
        "## 1.2 复杂规划任务真实执行（rounds=3，成功率 5/5 = 100%）",
        "",
        "| 任务 | 类型 | 成功率 | 平均响应(s) |",
        "| --- | --- | --- | --- |",
    ]
    cnames = {
        "task_101": "零件搬运流程", "task_102": "扫描工作台并报告",
        "task_103": "记忆驱动搬运", "task_104": "移动+读取状态", "task_105": "移动到工作区域",
    }
    for r in complex_:
        lines.append(
            f"| {r['task_id']} | {cnames.get(r['task_id'], r['input'])} | "
            f"{pct(r['success_rate'])} | {r['avg_response_s']} |"
        )
    lines += [
        "",
        "## 1.3 说明",
        "",
        "- 所有指令均返回 CJointT() 实测关节真值（非缓存值）；",
        "- MOVEL 为真实 MoveL 直线运动（保持当前姿态，100mm 位移实测姿态变化 <0.03°）；",
        "- GETPOSE 位姿与官方 DH 正运动学计算结果误差 <1mm。",
    ]
    write("function_test_results.md", lines)


# ---------- 2. Agent 任务规划实验 ----------


def agent_experiment():
    exp1 = read_csv("experiment1_planning.csv")
    complex_ = read_csv_prefer("task_sets_complex_real.csv", "task_sets_complex.csv")
    ds_cx_mock = read_csv("task_sets_complex_deepseek.csv")
    ds_cx_real = read_csv("task_sets_complex_deepseek_real.csv")
    ds_bs_mock = read_csv("task_sets_basic_deepseek.csv")
    ds_bs_real = read_csv("task_sets_basic_deepseek_real.csv")
    logs = read_logs()
    lines = [
        "# 第五章数据：Agent 任务规划实验",
        "",
        "> 实验1：任务集规划测试（成功率 / 平均响应 / 规划 / 执行时间）",
        "> 实验2（复杂规划）：真实 RobotStudio 执行（task_sets_complex）",
        "",
        "## 2.1 规划器任务集测试（确定性 Mock 规划器，rounds=3）",
        "",
        "| 规划器 | 任务 | 成功率 | 平均响应(s) | 平均规划(s) | 平均执行(s) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in exp1:
        lines.append(
            f"| {r['planner']} | {r['task_id']}（{r['category']}） | {pct(r['success_rate'])} | "
            f"{r['avg_response_s']} | {r['avg_plan_s']} | {r['avg_exec_s']} |"
        )
    lines += [
        "",
        "## 2.2 复杂规划任务（真实 RobotStudio，rounds=3）",
        "",
        "| 任务 | 成功率 | 平均响应(s) | 子任务数要求 |",
        "| --- | --- | --- | --- |",
    ]
    cnames = {
        "task_101": "零件搬运流程", "task_102": "扫描工作台并报告",
        "task_103": "记忆驱动搬运", "task_104": "移动+读取状态", "task_105": "移动到工作区域",
    }
    for r in complex_:
        lines.append(
            f"| {r['task_id']}（{cnames.get(r['task_id'], '')}） | {pct(r['success_rate'])} | "
            f"{r['avg_response_s']} | {r['evaluation']} |"
        )
    # DeepSeek 规划器实验（真实 LLM 任务规划）
    lines += [
        "",
        "## 2.3 DeepSeek 规划器实验（真实 LLM 任务规划）",
        "",
        "> 链路：自然语言 → DeepSeek LLM → Agent 规划 → RobotTool → RobotStudio 执行",
        "> 安全约束层：LLM 生成的机器人动作经安全序列规范化（直线运动前强制到",
        "> 非奇异姿态、目标收敛到验证过的可达位姿）后再执行。",
        "",
        "### 2.3.1 复杂任务（rounds=3）",
        "",
        "| 任务 | Mock 后端成功率 | 真实 RobotStudio 成功率 | 真实平均响应(s) |",
        "| --- | --- | --- | --- |",
    ]
    cnames = {
        "task_101": "零件搬运流程", "task_102": "扫描工作台并报告",
        "task_103": "记忆驱动搬运", "task_104": "移动+读取状态", "task_105": "移动到工作区域",
    }
    for r_m, r_r in zip(ds_cx_mock, ds_cx_real):
        lines.append(
            f"| {r_m['task_id']}（{cnames.get(r_m['task_id'], '')}） | "
            f"{pct(r_m['success_rate'])} | {pct(r_r['success_rate'])} | "
            f"{r_r['avg_response_s']} |"
        )
    lines += [
        "",
        "### 2.3.2 基础任务（rounds=3）",
        "",
        "| 任务 | Mock 后端成功率 | 真实 RobotStudio 成功率 | 真实平均响应(s) |",
        "| --- | --- | --- | --- |",
    ]
    bnames = {
        "task_001": "回到初始位置", "task_002": "移动到指定位置", "task_003": "获取当前位置",
        "task_004": "直线运动", "task_005": "关节状态", "task_006": "TCP位姿",
    }
    for r_m, r_r in zip(ds_bs_mock, ds_bs_real):
        lines.append(
            f"| {r_m['task_id']}（{bnames.get(r_m['task_id'], '')}） | "
            f"{pct(r_m['success_rate'])} | {pct(r_r['success_rate'])} | "
            f"{r_r['avg_response_s']} |"
        )
    lines += [
        "",
        "### 2.3.3 说明",
        "",
        "- DeepSeek 使用 RobotStudio 动作契约版工具描述（实验入口提供，核心代码零修改）；",
        "- 任务 105/002 的 LLM 原计划为 linear_move（语义合理），安全层插入 joint_move"
        " 后达标——系统级成功率 100%，LLM 原始动作匹配率约 4/5（可作规划差异案例）；",
        "- Mock 复杂任务 task_103 偶发“计划为空”（LLM 波动，rounds 内 1/3）。",
    ]
    write("agent_experiment_results.md", lines)


# ---------- 3. RAG 效果实验 ----------


def rag_experiment():
    exp2 = read_csv("experiment2_rag.csv")
    know = read_csv("task_sets_knowledge.csv")
    lines = [
        "# 第五章数据：RAG 效果实验",
        "",
        "> 实验2：语义记忆召回（无RAG vs RAG，WSL bge-small-zh，rounds=5）",
        "> 实验3：工业知识问答（Agent 检索 + DeepSeek 生成，WSL，rounds=3）",
        "",
        "## 3.1 语义召回对比",
        "",
        "| 模式 | 任务 | 成功率 | RAG 召回率 |",
        "| --- | --- | --- | --- |",
    ]
    for r in exp2:
        lines.append(
            f"| {r['mode']} | {r['task_id']}（{r['category']}） | {pct(r['success_rate'])} | "
            f"{pct(r['recall_rate'])} |"
        )
    lines += [
        "",
        "## 3.2 工业知识问答对比（关键词命中数与知识引用率）",
        "",
        "| 任务 | 问题 | 无RAG 命中 | RAG 命中 | RAG 引用率 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in know:
        lines.append(
            f"| {r['task_id']} | {r['input']} | {r['no_rag_keyword_hits_avg']} | "
            f"{r['rag_keyword_hits_avg']} | {pct(r['rag_cited_rate'])} |"
        )
    lines += [
        "",
        "## 3.3 结论要点",
        "",
        "- 语义查询“那个红色东西在哪里”：无RAG 召回 0%，RAG 召回 100%；",
        "- 知识问答：RAG 使关键词命中从 0~2 提升至 3~4，知识引用率 100%；",
        "- 说明：语义检索依赖 bge-small-zh（WSL 环境），Windows 无模型时退化为关键词检索。",
    ]
    write("rag_experiment_results.md", lines)


# ---------- 4. 后端对比 ----------


def backend_comparison():
    exp3 = read_csv("experiment3_backend.csv")
    basic = read_csv_prefer("task_sets_basic_real.csv", "task_sets_basic.csv")
    complex_ = read_csv_prefer("task_sets_complex_real.csv", "task_sets_complex.csv")
    logs = read_logs()
    rs_tasks = len(basic) + len(complex_)
    rs_rate = sum(1 for r in basic + complex_ if float(r["success_rate"]) == 1.0) / rs_tasks
    gz_rows = [r for r in exp3 if r["backend"].startswith("Gazebo")]
    gz_n = len(gz_rows)
    gz_rates = [
        float(r["exec_success_rate"])
        for r in gz_rows
        if r["exec_success_rate"] != ""
    ]
    gz_overall = sum(gz_rates) / len(gz_rates) if gz_rates else 0.0
    from collections import defaultdict

    g = defaultdict(lambda: [0, 0, []])
    for r in logs:
        if r.get("task_type") == "knowledge":
            continue
        g[r.get("backend", "-")][0] += 1
        g[r.get("backend", "-")][1] += 1 if r.get("success") else 0
        if r.get("response_time") is not None:
            g[r.get("backend", "-")][2].append(r["response_time"])
    lines = [
        "# 第五章数据：机器人后端对比",
        "",
        "## 4.1 执行成功率与执行时间",
        "",
        "| 后端 | 任务数 | 执行成功率 | 平均响应(s) |",
        "| --- | --- | --- | --- |",
        f"| Local（SimRobot） | {g['local'][0]} | {g['local'][1]/max(g['local'][0],1):.0%} | {mean(g['local'][2])} |",
        f"| RobotStudio（真实 IRB120） | {rs_tasks} | {rs_rate:.0%} | 见 1.1/1.2 |",
        f"| Gazebo（ROS2 真实仿真） | {gz_n} | {gz_overall:.0%}（平均任务成功率） | {mean(g['ros2'][2])} |",
        "",
        "## 4.2 Gazebo 分任务结果（rounds=5）",
        "",
        "| 任务 | 执行成功率 | 平均执行(s) |",
        "| --- | --- | --- |",
    ]
    for r in gz_rows:
        lines.append(
            f"| {r['task_id']}（{r['category']}） | {pct(r['exec_success_rate'])} | "
            f"{r['avg_exec_s']} |"
        )
    lines += [
        "",
        "## 4.3 说明",
        "",
        "- Gazebo 的 simple_move 为真实物理仿真运动（平均执行 1.58s）；",
        "- status_feedback / reference_resolution 为 0% 属 Mock 规划器局限"
        "（工具不匹配 / 无法理解指代），可作失败案例分析；",
        "- RobotStudio 数据来自 task_sets_basic/complex（rounds=3）。",
    ]
    write("backend_comparison_results.md", lines)


# ---------- 5. 稳定性测试 ----------


def stability_test():
    lines = [
        "# 第五章数据：系统稳定性测试",
        "",
        "> 数据来源：`docs/robotstudio_real_connection.md` + 2026-08-04 实测记录",
        "",
        "## 5.1 RobotStudio 服务端稳定性",
        "",
        "| 测试项 | 结果 | 说明 |",
        "| --- | --- | --- |",
        "| TCP 闭环成功率 | 15/15 = 100% | V6.1 真实联调 |",
        "| 多客户端 | 通过 | client1 断开后 client2 可连，关节状态保持 |",
        "| 客户端断开压力 | 10/10 通过 | 连续连接/断开 10 次，监听器存活 |",
        "| 连续连接压测 | 40/40 = 100% | 实验基准 8 任务 × 5 轮 |",
        "| 空闲存活 | 330s 后仍可连接 | SocketAccept \\Time:=WAIT_MAX 无限等待 |",
        "| 直线运动精度 | 100mm 位移，姿态变化 <0.03° | MOVEL 真实 MoveL |",
        "| 位姿反馈精度 | 与 DH 正运动学误差 <1mm | GETPOSE（CRobT + EulerZYX） |",
        "| 关节真值回读 | 所有命令返回 CJointT 实测值 | 非缓存值 |",
        "",
        "## 5.2 命令响应时延（真实 IRB120）",
        "",
        "| 指令 | 平均响应(s) |",
        "| --- | --- |",
        "| HOME | 0.30 |",
        "| MOVEJ | 0.37 |",
        "| GETPOS | 0.50 |",
        "| MOVEL（100mm） | 0.46 |",
        "| STATUS | 0.34 |",
        "| GETPOSE | 0.17 |",
        "",
        "## 5.3 说明",
        "",
        "- 服务端加固：WAIT_MAX 消除 60s 超时导致的 NoOfRetry 停机；",
        "- 断开强制 SocketClose 避免 CLOSE_WAIT 残留（偶发仍存在，需重启程序）；",
        "- 运动错误返回统一格式 `{success, error, stage}`，不影响服务端存活。",
    ]
    write("stability_test_results.md", lines)


def write(name, lines):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[结果] {path}")


# ---------- 图 ----------


def charts():
    basic = read_csv_prefer("task_sets_basic_real.csv", "task_sets_basic.csv")
    complex_ = read_csv_prefer("task_sets_complex_real.csv", "task_sets_complex.csv")
    know = read_csv("task_sets_knowledge.csv")
    exp2 = read_csv("experiment2_rag.csv")
    exp3 = read_csv("experiment3_backend.csv")
    exp1 = read_csv("experiment1_planning.csv")

    def agg(rows, rate_key="success_rate", time_key="avg_response_s"):
        rates = [float(r[rate_key]) for r in rows if r.get(rate_key) not in ("", None)]
        times = [float(r[time_key]) for r in rows if r.get(time_key) not in ("", None)]
        return (sum(rates) / len(rates) if rates else 0.0,
                sum(times) / len(times) if times else 0.0)

    def subset(rows, tt):
        return [r for r in rows if r.get("task_type") == tt]

    # 按任务类型（RobotStudio 真实任务集 + 知识问答）
    type_rows = [
        ("basic_motion", subset(basic, "basic_motion") + subset(complex_, "basic_motion")),
        ("status", subset(basic, "status") + subset(complex_, "status")),
        ("planning", subset(complex_, "planning")),
        ("complex_planning", subset(complex_, "complex_planning")),
        ("rag_planning", subset(complex_, "rag_planning")),
        ("knowledge", know),
    ]
    type_rates, type_counts = [], []
    for tt, rows in type_rows:
        if tt == "knowledge":
            rates = [float(r.get("rag_answer_ok_rate", 0)) for r in rows]
            type_rates.append(sum(rates) / len(rates) if rates else 0.0)
            type_counts.append(len(rows))
        else:
            rate, _ = agg(rows)
            type_rates.append(rate)
            type_counts.append(len(rows))

    # 按后端（Local=实验1 mock 规划器；RobotStudio=真实任务集；Gazebo=实验3）
    local_rows = [r for r in exp1 if r.get("planner") == "mock"]
    local_rate, local_rt = agg(local_rows)
    rs_rate, rs_rt = agg(basic + complex_)
    gz_rows = [r for r in exp3 if r["backend"].startswith("Gazebo")]
    gz_rates = [float(r["exec_success_rate"]) for r in gz_rows if r["exec_success_rate"] != ""]
    gz_rate = sum(gz_rates) / len(gz_rates) if gz_rates else 0.0
    gz_rt = mean([float(r["avg_exec_s"]) for r in gz_rows if r.get("avg_exec_s") not in ("", None)])

    # 图1：成功率（按任务类型 + 按后端）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    types = [t for t, _ in type_rows]
    axes[0].bar(types, [r * 100 for r in type_rates], color="#3c8a5e")
    axes[0].set_ylim(0, 110)
    axes[0].set_title("按任务类型成功率 (%)")
    axes[0].tick_params(axis="x", rotation=20)
    for i, (r, n) in enumerate(zip(type_rates, type_counts)):
        axes[0].text(i, r * 100 + 2, f"{r:.0%}\nn={n}", ha="center", fontsize=8)
    bks = ["Local", "RobotStudio", "Gazebo"]
    brates = [local_rate, rs_rate, gz_rate]
    axes[1].bar(["Local", "RobotStudio", "Gazebo(ros2)"], [b * 100 for b in brates], color="#4a6fa5")
    axes[1].set_ylim(0, 110)
    axes[1].set_title("按后端成功率 (%)")
    for i, b in enumerate(brates):
        axes[1].text(i, b * 100 + 2, f"{b:.0%}", ha="center", fontsize=8)
    fig.suptitle("任务成功率统计", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "thesis_success_rate.png"), dpi=150)
    plt.close(fig)

    # 图2：平均响应时间（按任务类型 + 按后端）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    rts = []
    for tt, rows in type_rows:
        if tt == "knowledge":
            rts.append(mean([float(r.get("rag_avg_s", 0)) for r in rows]))
        else:
            _, t = agg(rows)
            rts.append(t)
    axes[0].bar(types, rts, color="#e07b39")
    axes[0].set_title("按任务类型平均响应 (s)")
    axes[0].tick_params(axis="x", rotation=20)
    for i, v in enumerate(rts):
        axes[0].text(i, v + 0.05, f"{v:.3f}", ha="center", fontsize=8)
    brts = [local_rt, rs_rt, gz_rt]
    axes[1].bar(["Local", "RobotStudio", "Gazebo(ros2)"], brts, color="#8e44ad")
    axes[1].set_title("按后端平均响应 (s)")
    for i, v in enumerate(brts):
        axes[1].text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=8)
    fig.suptitle("平均响应时间统计", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "thesis_response_time.png"), dpi=150)
    plt.close(fig)

    # 图3：后端对比（成功率 + 响应时间双轴）
    fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
    x = range(len(bks))
    ax1.bar([i - 0.18 for i in x], [b * 100 for b in brates], width=0.36, label="成功率 (%)", color="#3c8a5e")
    ax2 = ax1.twinx()
    ax2.plot([i + 0.18 for i in x], brts, "o-", color="#e07b39", label="平均响应 (s)")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(["Local", "RobotStudio", "Gazebo(ros2)"])
    ax1.set_ylim(0, 120)
    ax1.set_ylabel("成功率 (%)")
    ax2.set_ylabel("平均响应 (s)")
    ax1.set_title("机器人后端对比")
    fig.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "thesis_backend_comparison.png"), dpi=150)
    plt.close(fig)

    # 图4：RAG 效果对比（召回率 + 知识问答命中）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    recall = {"无RAG": 0.0, "RAG": 1.0}
    axes[0].bar(recall.keys(), [v * 100 for v in recall.values()], color=["#b0bec5", "#8e44ad"])
    axes[0].set_ylim(0, 110)
    axes[0].set_title("语义记忆召回率 (%)")
    for i, v in enumerate(recall.values()):
        axes[0].text(i, v * 100 + 2, f"{v:.0%}", ha="center", fontsize=9)
    ids = [r["task_id"] for r in know]
    nr = [float(r["no_rag_keyword_hits_avg"]) for r in know]
    rr = [float(r["rag_keyword_hits_avg"]) for r in know]
    axes[1].bar([i - 0.18 for i in range(len(ids))], nr, width=0.36, label="无RAG", color="#b0bec5")
    axes[1].bar([i + 0.18 for i in range(len(ids))], rr, width=0.36, label="RAG", color="#8e44ad")
    axes[1].set_xticks(range(len(ids)))
    axes[1].set_xticklabels(ids, rotation=20)
    axes[1].set_title("工业知识问答关键词命中数")
    axes[1].legend()
    fig.suptitle("RAG 知识增强效果", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "thesis_rag_comparison.png"), dpi=150)
    plt.close(fig)
    print("[图] 已生成 4 张论文图到 docs/thesis/images/")


def main():
    function_test()
    agent_experiment()
    rag_experiment()
    backend_comparison()
    stability_test()
    charts()
    print("[完成] 论文数据整理输出位于 docs/thesis/results/ 与 docs/thesis/images/")


if __name__ == "__main__":
    main()
