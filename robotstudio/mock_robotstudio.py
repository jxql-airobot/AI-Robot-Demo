# -*- coding: utf-8 -*-
"""
mock_robotstudio.py — Mock RobotStudio 服务端 (V6.0)
====================================================
在没有 RobotStudio/RobotWare 时，用本地 TCP 服务端模拟 ABB 虚拟控制器，
实现与 RAPID SocketServer 相同的文本协议，保证 Agent 全链路可测试。

用法：
    server = MockRobotStudioServer(port=0)   # port=0 自动分配
    server.start()
    client = RobotStudioClient(host, server.port, mock=False)
"""

import socket
import threading

from robotstudio.command_schema import build_command, parse_reply


class MockRobotStudioServer:
    """模拟 ABB 虚拟控制器：监听 TCP，执行文本命令并回复"""

    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.port = port
        self.joints = [0.0] * 6      # 当前关节角度
        self.last_action = None      # 最后执行的动作
        self._server = None
        self._thread = None
        self._running = False

    def start(self):
        """启动 TCP 服务端"""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(1)
        self.port = self._server.getsockname()[1]
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        return self.port

    def stop(self):
        """关闭服务端"""
        self._running = False
        try:
            if self._server:
                self._server.close()
        except OSError:
            pass

    def _accept_loop(self):
        while self._running:
            try:
                conn, _ = self._server.accept()
            except OSError:
                break
            handler = threading.Thread(target=self._handle_conn, args=(conn,), daemon=True)
            handler.start()

    def _handle_conn(self, conn):
        """处理单个连接：按行读取命令并回复"""
        try:
            conn.settimeout(10.0)
            buf = b""
            while self._running:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    reply = self._execute(line.decode("utf-8", errors="ignore"))
                    conn.sendall((reply + "\n").encode("utf-8"))
        except (OSError, socket.timeout):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _execute(self, line):
        """执行一条命令，返回回复文本"""
        cmd = line.strip().upper()
        if not cmd:
            return "ERROR 空命令"
        if cmd == "HOME":
            self.joints = [0.0] * 6
            self.last_action = "move_home"
            return f"OK {','.join(str(j) for j in self.joints)}"
        if cmd.startswith("MOVEJ"):
            try:
                values = [float(x) for x in cmd[5:].strip().split(",")]
                if len(values) != 6:
                    return "ERROR MOVEJ 需要 6 个关节角度"
                self.joints = values
                self.last_action = "joint_move"
                return f"OK {','.join(str(j) for j in self.joints)}"
            except ValueError:
                return "ERROR MOVEJ 参数无法解析"
        if cmd.startswith("MOVEL"):
            self.last_action = "linear_move"
            return f"OK {','.join(str(j) for j in self.joints)}"
        if cmd == "GETPOS" or cmd == "STATUS":
            return f"OK {','.join(str(j) for j in self.joints)}"
        return f"ERROR 未知命令: {cmd}"


def main():
    """独立运行 Mock 服务端（调试用）"""
    server = MockRobotStudioServer(port=30000)
    server.start()
    print(f"Mock RobotStudio 监听 {server.host}:{server.port}，Ctrl+C 退出")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
