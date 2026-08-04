# -*- coding: utf-8 -*-
"""
robotstudio_client.py — RobotStudio TCP 客户端 (V6.0)
=====================================================
AI Agent 与 RobotStudio 虚拟控制器之间的通信层。

真实模式：连接 RobotStudio 虚拟控制器（RAPID SocketServer，见 rapid/socket_server.mod）
Mock 模式：本地启动 MockRobotStudioServer，协议完全一致。

用法：
    client = RobotStudioClient(host, port, mock=True)
    client.connect()
    reply = client.send_action({"action": "move_home"})
    client.close()
"""

import socket

from robotstudio.command_schema import build_command, parse_reply
from robotstudio.mock_robotstudio import MockRobotStudioServer


class RobotStudioClient:
    """RobotStudio 虚拟控制器 TCP 客户端"""

    def __init__(self, host="127.0.0.1", port=30000, timeout_seconds=5.0, mock=True):
        self.host = host
        self.port = port
        self.timeout = timeout_seconds
        self.mock = mock
        self._mock_server = None
        self._sock = None
        if mock:
            self._mock_server = MockRobotStudioServer(host="127.0.0.1", port=0)

    @property
    def connected(self):
        return self._sock is not None

    def connect(self):
        """建立 TCP 连接（Mock 模式自动启动本地服务端）"""
        if self.connected:
            return True
        if self._mock_server is not None:
            self.port = self._mock_server.start()
        self._sock = socket.create_connection(
            (self.host, self.port), timeout=self.timeout
        )
        self._sock.settimeout(self.timeout)
        return True

    def send_action(self, action):
        """发送一条动作命令，返回解析后的回复 dict"""
        self.connect()
        cmd = build_command(action)
        self._sock.sendall(cmd.encode("utf-8"))
        line = self._recv_line()
        return parse_reply(line)

    def get_position(self):
        """查询当前关节位置"""
        return self.send_action({"action": "get_position"})

    def close(self):
        """关闭连接与 Mock 服务端"""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._mock_server is not None:
            self._mock_server.stop()

    def _recv_line(self):
        """按行读取服务端回复"""
        buf = b""
        while True:
            chunk = self._sock.recv(1024)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                line, _ = buf.split(b"\n", 1)
                return line.decode("utf-8", errors="ignore")
        return buf.decode("utf-8", errors="ignore")
