#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后台空闲存活探测：等待 N 秒后连接 RobotStudio 30000 端口并写结果文件"""

import socket
import sys
import time

WAIT_SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 330
OUT = sys.argv[2] if len(sys.argv) > 2 else "idle_probe_result.txt"

time.sleep(WAIT_SECONDS)
s = socket.socket()
s.settimeout(8)
try:
    s.connect(("127.0.0.1", 30000))
    s.sendall(b"GETPOS\n")
    data = s.recv(1024).decode("utf-8", "ignore").strip()
    result = f"ALIVE after {WAIT_SECONDS}s idle: {data}"
except Exception as exc:
    result = f"DEAD after {WAIT_SECONDS}s idle: {exc!r}"
finally:
    s.close()

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(result)
print(result)
