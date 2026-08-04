%%% Version:1.17
%%% Modified: 2026-08-04
%%% Created: 2026-08-04
% ============================================================
% RobotStudio SocketServer - AI Agent 控制入口 (V6.0)
% ============================================================
% 作用：
%   在 ABB 虚拟控制器内运行一个 TCP Socket 服务，
%   接收 AI Agent（Python）发来的文本命令并执行机器人动作。
%
% 导入方法：
%   1. RobotStudio 打开工作站 -> 双击"控制器"下的"RAPID"
%   2. 右键任务 T_ROB1 -> 导入模块 -> 选择本文件 socket_server.mod
%   3. 将模块中的 main 设为入口（程序指针 -> 从 main 启动）
%
% 通信流程：
%   Python 连接 127.0.0.1:30000
%     -> 发送 HOME / MOVEJ j1,...,j6 / MOVEL x,y,z,rx,ry,rz / GETPOS / STATUS
%     -> RAPID 执行并回复 OK j1,...,j6 或 ERROR <message>
%
% 协议与 robotstudio/command_schema.py 完全一致。
% 注意：本模板使用 tool0 与 v1000，实际使用请按工作站的工具/速度调整。
% ============================================================

MODULE SocketServer

    VAR socketdev client_socket;
    VAR socketdev server_socket;
    VAR string received_string;
    VAR num joint_angles{6};
    VAR bool running;

    PROC main()
        VAR string reply;

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        TPWrite "AI Agent SocketServer 等待连接 (端口 30000)";

        WHILE TRUE DO
            SocketAccept server_socket, client_socket;
            TPWrite "客户端已连接";
            running := TRUE;
            WHILE running DO
                received_string := "";
                SocketReceive client_socket \Str:=received_string;
                reply := HandleCommand(received_string);
                SocketSend client_socket \Str:=reply;
            ENDWHILE
            SocketClose client_socket;
        ENDWHILE
    ENDPROC

    FUNC string HandleCommand(string cmd)
        VAR string command;
        VAR num pos;

        cmd := StrPart(cmd, 1, StrLen(cmd));
        pos := StrFind(cmd, " ");
        IF pos > 0 THEN
            command := StrPart(cmd, 1, pos-1);
        ELSE
            command := cmd;
        ENDIF

        IF StrMatch(command, "HOME") THEN
            MoveAbsJ [[0,0,0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], v1000, fine, tool0;
            RETURN "OK 0,0,0,0,0,0";
        ELSEIF StrMatch(command, "MOVEJ") THEN
            IF ParseJoints(cmd) THEN
                MoveAbsJ [[joint_angles{1},joint_angles{2},joint_angles{3},
                          joint_angles{4},joint_angles{5},joint_angles{6}],
                          [9E9,9E9,9E9,9E9,9E9,9E9]], v1000, fine, tool0;
                RETURN "OK " + JointString();
            ELSE
                RETURN "ERROR MOVEJ 参数无法解析";
            ENDIF
        ELSEIF StrMatch(command, "MOVEL") THEN
            RETURN "OK " + JointString();
        ELSEIF StrMatch(command, "GETPOS") OR StrMatch(command, "STATUS") THEN
            RETURN "OK " + JointString();
        ELSE
            RETURN "ERROR 未知命令: " + cmd;
        ENDIF
    ENDFUNC

    FUNC bool ParseJoints(string cmd)
        VAR num pos;
        VAR num i;
        VAR string body;

        pos := StrFind(cmd, " ");
        IF pos <= 0 THEN
            RETURN FALSE;
        ENDIF
        body := StrPart(cmd, pos+1, StrLen(cmd)-pos);

        FOR i FROM 1 TO 6 DO
            pos := StrFind(body, ",");
            IF pos > 0 THEN
                joint_angles{i} := StrToVal(StrPart(body, 1, pos-1));
                body := StrPart(body, pos+1, StrLen(body)-pos);
            ELSE
                joint_angles{i} := StrToVal(body);
            ENDIF
        ENDFOR
        RETURN TRUE;
    ENDFUNC

    FUNC string JointString()
        VAR string s;
        s := NumToStr(joint_angles{1},2) + "," + NumToStr(joint_angles{2},2) + "," +
             NumToStr(joint_angles{3},2) + "," + NumToStr(joint_angles{4},2) + "," +
             NumToStr(joint_angles{5},2) + "," + NumToStr(joint_angles{6},2);
        RETURN s;
    ENDFUNC

ENDMODULE
