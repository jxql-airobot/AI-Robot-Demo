#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_environment.py — RobotStudio 环境检查 (V6.0 第二阶段)
===========================================================
检查：Python 版本 / RobotStudio 安装 / RobotWare 组件 /
      配置文件 / Socket 端口可用性。

用法：
    python robotstudio/check_environment.py            # 输出报告到控制台
    python robotstudio/check_environment.py --report   # 同时生成 docs/robotstudio_environment_report.md
"""

import argparse
import os
import socket
import subprocess
import sys

RS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(RS_DIR)
for p in (RS_DIR, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from robotstudio.config import load_config  # noqa: E402
from robotstudio.mock_robotstudio import MockRobotStudioServer  # noqa: E402

ROBOTSTUDIO_PATH = r"D:\Program Files (x86)\ABB Industrial IT\Robotics IT\RobotStudio 6.08"


def check_python():
    return {"python": sys.version.split()[0], "platform": sys.platform}


def check_robotstudio():
    exists = os.path.isdir(ROBOTSTUDIO_PATH)
    exe = os.path.isfile(os.path.join(ROBOTSTUDIO_PATH, "Bin", "RobotStudio.exe"))
    controllers_dll = os.path.isfile(
        os.path.join(ROBOTSTUDIO_PATH, "Bin", "ABB.Robotics.RobotStudio.Controllers.dll")
    )
    return {
        "installed": exists,
        "exe": exe,
        "controllers_dll": controllers_dll,
        "path": ROBOTSTUDIO_PATH,
    }


def check_robotware():
    """查询注册表中的 RobotWare / 控制器组件"""
    found = []
    try:
        import winreg

        roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        subkeys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        for root in roots:
            for subkey in subkeys:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        i = 0
                        while True:
                            try:
                                name = winreg.EnumKey(key, i)
                                i += 1
                                with winreg.OpenKey(key, name) as app:
                                    try:
                                        display = winreg.QueryValueEx(app, "DisplayName")[0]
                                    except OSError:
                                        continue
                                    if display and (
                                        "RobotWare" in display or "RobotStudio" in display
                                    ):
                                        try:
                                            version = winreg.QueryValueEx(app, "DisplayVersion")[0]
                                        except OSError:
                                            version = ""
                                        try:
                                            loc = winreg.QueryValueEx(app, "InstallLocation")[0]
                                        except OSError:
                                            loc = ""
                                        found.append(
                                            {"name": display, "version": version, "location": loc}
                                        )
                            except OSError:
                                break
                except OSError:
                    continue
    except ImportError:
        pass
    robotware = [f for f in found if "RobotWare" in f["name"]]
    return {"found": found, "robotware": robotware}


def check_config():
    cfg = load_config()
    return cfg


def check_port():
    """用 Mock 服务端验证本地端口能力；并尝试探测配置中的真实端口"""
    server = MockRobotStudioServer(port=0)
    port = server.start()
    server.stop()
    probe = {"mock_port_ok": port > 0, "mock_port": port}
    cfg = load_config()
    if cfg.get("backend") == "real":
        try:
            with socket.create_connection(
                (cfg["host"], int(cfg["port"])), timeout=2
            ):
                probe["real_port_reachable"] = True
        except OSError:
            probe["real_port_reachable"] = False
    else:
        probe["real_port_reachable"] = None  # 未启用真实模式
    return probe


def main():
    parser = argparse.ArgumentParser(description="RobotStudio 环境检查")
    parser.add_argument("--report", action="store_true", help="生成环境报告 md")
    args = parser.parse_args()

    report = {
        "python": check_python(),
        "robotstudio": check_robotstudio(),
        "robotware": check_robotware(),
        "config": check_config(),
        "port": check_port(),
    }

    lines = ["# RobotStudio 环境检查报告", ""]
    lines.append("## 1. Python")
    lines.append(f"- 版本：{report['python']['python']}（{report['python']['platform']}）")
    lines.append("")
    lines.append("## 2. RobotStudio")
    rs = report["robotstudio"]
    mark = lambda ok: "[OK]" if ok else "[缺失]"
    lines.append(f"- 路径存在：{mark(rs['installed'])} `{rs['path']}`")
    lines.append(f"- RobotStudio.exe：{mark(rs['exe'])}")
    lines.append(f"- Controllers.dll：{mark(rs['controllers_dll'])}")
    lines.append("")
    lines.append("## 3. RobotWare / ABB 组件")
    if report["robotware"]["found"]:
        for f in report["robotware"]["found"]:
            lines.append(f"- {f['name']} {f['version']}（{f['location'] or '位置未知'}）")
    else:
        lines.append("- [警告] 未检测到 RobotWare / RobotStudio 注册组件（RobotWare 6.08 需单独安装）")
    lines.append("")
    lines.append("## 4. 配置文件（robotstudio/config.json）")
    for k, v in report["config"].items():
        lines.append(f"- `{k}`：`{v}`")
    lines.append("")
    lines.append("## 5. Socket 端口")
    lines.append(f"- Mock 端口可用：{mark(report['port']['mock_port_ok'])}")
    if report["port"]["real_port_reachable"] is None:
        lines.append("- 真实端口：未启用（backend=mock）")
    else:
        lines.append(
            f"- 真实端口可达：{mark(report['port']['real_port_reachable'])}"
        )
    text = "\n".join(lines) + "\n"

    print(text)
    if args.report:
        out = os.path.join(REPO_ROOT, "docs", "robotstudio_environment_report.md")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"[报告] 已生成: {out}")


if __name__ == "__main__":
    main()
