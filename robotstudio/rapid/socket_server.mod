%%% Version:1.17
%%% Modified: 2026-08-04
%%% Created: 2026-08-04
% "RobotStudio SocketServer - AI Agent 控制入口 (V6.0)"
% 导入到 RobotStudio 的 RAPID 程序模块。
% 协议与 robotstudio/command_schema.py 一致：
%   客户端 -> HOME / MOVEJ j1,...,j6 / MOVEL x,y,z,rx,ry,rz / GETPOS
%   服务端 -> OK j1,...,j6 或 ERROR <message>

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
        command := StrPart(cmd, 1, StrFind(cmd, " ")-1);
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
        ELSEIF StrMatch(command, "GETPOS") THEN
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
        IF pos <= 0 THEN RETURN FALSE; ENDIF
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
        s := NumToStr(joint_angles{1},0) + "," + NumToStr(joint_angles{2},0) + "," +
             NumToStr(joint_angles{3},0) + "," + NumToStr(joint_angles{4},0) + "," +
             NumToStr(joint_angles{5},0) + "," + NumToStr(joint_angles{6},0);
        RETURN s;
    ENDFUNC

ENDMODULE
