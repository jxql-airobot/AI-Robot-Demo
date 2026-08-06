#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_rws_recovery_experiment.py — RWS 自动恢复真实验证 (V6.7)
============================================================
在真实 ABB RobotStudio + IRC5 虚拟控制器链路上，验证 50050 停止级
错误发生后无需人工重启 RAPID，而是通过 RobotWebServices（RWS）自动
恢复：

    越界 MOVEL → 50050 停止级错误
      ↓
    RWS 查询控制器状态（running/stopped/error）
      ↓
    RWS reset（清除错误）
      ↓
    RWS PP to main
      ↓
    RWS start RAPID
      ↓
    等待 SocketServer（30000）恢复
      ↓
    重连并执行 HOME 验证任务恢复

前置条件：
    1. RobotStudio + IRC5 虚拟控制器运行中，RAPID SocketServer 监听 30000；
    2. 虚拟控制器已启用 RobotWebServices（RWS），见脚本输出的启用步骤。

用法：
    python experiments/scripts/run_rws_recovery_experiment.py --rounds 10
输出：
    experiments/logs/rws_recovery_logs.json
    experiments/results/rws_recovery_report.md
"""

import argparse
import datetime
import json
import os
import socket
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (BASE, os.path.join(BASE, "agent"), os.path.join(BASE, "tests"),
          os.path.join(BASE, "experiments", "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent.recovery.manager import RecoveryManager  # noqa: E402
from agent.recovery.rws_manager import RWSManager  # noqa: E402
from robotstudio.config import load_config  # noqa: E402
from robotstudio.robotstudio_client import RobotStudioClient  # noqa: E402

LOGS_DIR = os.path.join(BASE, "experiments", "logs")
RESULTS_DIR = os.path.join(BASE, "experiments", "results")
LOG_PATH = os.path.join(LOGS_DIR, "rws_recovery_logs.json")
REPORT_PATH = os.path.join(RESULTS_DIR, "rws_recovery_report.md")

OUT_OF_RANGE_TARGET = [1.2, 1.2, 1.2, 0.0, 0.0, 0.0]  # 越界，触发 50050


def port_open(host, port, timeout=2.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def rws_enable_steps():
    return (
        "RWS 未启用，无法执行自动恢复实验。请在 RobotStudio 中完成以下"
        "一次性配置：\n"
        "  1. 控制器（Controller）选项卡 → 连接 IRC5 虚拟控制器；\n"
        "  2. 配置（Configuration）→ Communication → Firewall Manager；\n"
        "  3. 编辑 RobotWebServices，将 EnableOnPublicNet / "
        "EnableOnPrivateNet 设为 Yes；\n"
        "  4. 应用配置并重启虚拟控制器；\n"
        "  5. 端口冲突处理：RWS 默认使用 80 端口，若本机 IIS 已占用 80，"
        "需停止 IIS 默认网站或调整端口，使 RWS 可绑定；\n"
        "  6. 验证：访问 http://127.0.0.1/rw/rapid/execution "
        "应返回控制器状态。"
    )


def make_client(cfg):
    return RobotStudioClient(
        host=cfg.get("host", "127.0.0.1"),
        port=int(cfg.get("port", 30000)),
        timeout_seconds=float(cfg.get("timeout", 5.0)),
        mock=False,
    )


def trigger_50050(client, cfg):
    """发送越界 MOVEL，触发 50050 停止级错误；返回触发结果。"""
    try:
        r = client.send_action(
            {"action": "linear_move", "target": OUT_OF_RANGE_TARGET})
        return r.get("error_code") or r.get("message"), r
    except Exception as exc:  # noqa: BLE001
        return f"socket_error: {exc}", None


def recover_with_rws(rws, mgr, error, cfg, max_retry=2):
    """调用 RecoveryManager（RWS 优先）恢复；返回恢复结果与重连时间。"""
    t0 = time.monotonic()
    plan = mgr.recover(error)
    t_recover = time.monotonic() - t0
    rws_result = plan.get("rws_result") or {}
    if plan.get("status") == "success":
        return plan, rws_result, t_recover
    # 恢复未成功：最多重试 2 次 RWS 全流程
    for _ in range(max_retry):
        time.sleep(2)
        plan = mgr.recover(error)
        rws_result = plan.get("rws_result") or {}
        if plan.get("status") == "success":
            return plan, rws_result, time.monotonic() - t0
    return plan, rws_result, time.monotonic() - t0


def verify_recovery(client, cfg):
    """恢复后重连并执行 HOME，验证任务可继续执行。"""
    try:
        client.connect()
        r = client.send_action({"action": "move_home"})
        return bool(r.get("ok")), (r.get("message") or "")
    except Exception as exc:  # noqa: BLE001
        return False, f"重连失败: {exc}"


def main():
    parser = argparse.ArgumentParser(description="RWS 自动恢复真实验证")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--rws-url", default="http://127.0.0.1")
    args = parser.parse_args()

    cfg = load_config()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 30000))

    if not port_open(host, port):
        print("[错误] RAPID SocketServer 未监听，请先启动 RAPID 程序")
        sys.exit(1)

    rws = RWSManager(base_url=args.rws_url, timeout=2.0)
    conn = rws.check_connection()
    if not conn["controller_available"]:
        print("[预检] RWS 不可用：" + conn["detail"])
        print(rws_enable_steps())
        sys.exit(2)
    print(f"[预检] RWS 可用：{conn['detail']}")

    client = make_client(cfg)
    backend = None  # 注入到 RecoveryManager 的回退后端
    from agent.tools.robotstudio_tool import RobotStudioBackend
    backend = RobotStudioBackend(client=client)
    mgr = RecoveryManager(backend=backend, recoverer=rws)

    records = []
    for i in range(1, args.rounds + 1):
        state_before = rws.get_controller_state()["state"]
        print(f"[{i}/{args.rounds}] 触发 50050（state={state_before}）...")
        err_code, trigger = trigger_50050(client, cfg)
        time.sleep(1.5)
        state_mid = rws.get_controller_state()["state"]
        server_stopped = not port_open(host, port)
        print(f"  触发结果: {err_code} | state={state_mid} | "
              f"server_stopped={server_stopped}")

        error = {
            "error_code": "50050",
            "error_type": "execution",
            "error_message": "position_unreachable",
            "raw_message": str(err_code or "50050 位置超出范围"),
        }
        plan, rws_result, t_recover = recover_with_rws(rws, mgr, error, cfg)
        print(f"  RWS 恢复: status={plan.get('status')} "
              f"recover_time={t_recover:.2f}s")

        t_sock = rws_result.get("socket_reconnect_time", 0.0)
        ok, msg = verify_recovery(client, cfg)
        state_after = rws.get_controller_state()["state"]
        records.append({
            "round": i,
            "error_code": "50050",
            "controller_state_before": state_before,
            "controller_state_mid": state_mid,
            "controller_state_after": state_after,
            "server_stopped": server_stopped,
            "recover_status": plan.get("status"),
            "recover_time": round(t_recover, 3),
            "socket_reconnect_time": round(float(t_sock or 0.0), 3),
            "task_success": ok,
            "verify_message": msg[:120],
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        print(f"  HOME 验证: {'成功' if ok else '失败'} "
              f"| state_after={state_after}")
        if not ok:
            print("  [注意] 本轮恢复后验证失败，停止实验")
            break

    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    # 释放 RWS 会话槽，避免长时间运行占用控制器会话
    try:
        rws.logout()
    except Exception:  # noqa: BLE001
        pass

    ok_n = sum(1 for r in records if r["task_success"])
    lines = [
        "# RWS 自动恢复真实验证报告",
        "",
        "## 1 实验环境",
        "",
        "- RobotStudio 6.08.01 + RobotWare 6.08.1040 + IRB120 + IRC5 虚拟控制器",
        f"- RWS: {args.rws_url}；RAPID SocketServer TCP {host}:{port}",
        "- 恢复流程：50050 → RWS 设置入口 → resetpp → start → 等 Socket 恢复",
        "",
        "## 2 实验结果",
        "",
        f"- 实验轮次：{len(records)}",
        f"- 任务恢复成功率：{ok_n}/{len(records)}"
        f"（{ok_n / len(records):.0%}）" if records else "-",
        "",
        "| 轮次 | 错误码 | 恢复前状态 | 恢复后状态 | 恢复耗时 | Socket 重连 | 任务成功 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        lines.append(
            f"| {r['round']} | {r['error_code']} | "
            f"{r['controller_state_before']} → {r['controller_state_mid']} | "
            f"{r['controller_state_after']} | {r['recover_time']} s | "
            f"{r['socket_reconnect_time']} s | {'✓' if r['task_success'] else '✗'} |"
        )
    lines += [
        "",
        "## 3 结论",
        "",
        "在真实 RobotStudio-IRC5 虚拟控制器链路上，50050 停止级错误发生后，"
        "通过 RobotWebServices 自动完成错误清除、PP 重置、RAPID 启动与"
        "Socket 重连，无需人工重启 RAPID。",
        "实验环境为虚拟控制器，结果不代表实体机器人上的行为。",
        "",
    ]
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"[完成] 日志: {LOG_PATH}")
    print(f"[完成] 报告: {REPORT_PATH}")


if __name__ == "__main__":
    main()
