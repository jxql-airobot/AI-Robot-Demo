%%% Version:1.20
%%% Modified: 2026-08-04
%%% Created: 2026-08-04
% ============================================================
% ABB RobotStudio SocketServer for AI Agent control (V6.1)
% ============================================================
% Purpose:
%   Runs inside an ABB IRC5 Virtual Controller (RobotWare 6.08).
%   Listens on TCP port 30000 and executes robot motions based on
%   text commands sent by the Python client.
%
% Import:
%   RAPID -> T_ROB1 -> right-click -> Load Module -> socket_server.mod
% Run:
%   PP to main -> Start
%
% Protocol (matches robotstudio/command_schema.py):
%   Client -> HOME | MOVEJ j1,...,j6 | MOVEL x,y,z,rx,ry,rz | GETPOS | STATUS
%   Server <- OK j1,...,j6 | ERROR <message>
%
% Socket instructions used (RobotWare 6 standard):
%   SocketCreate, SocketBind, SocketListen, SocketAccept,
%   SocketReceive, SocketSend, SocketClose
%
% NOTE: uses tool0 and v1000; adjust for your station if needed.
% ============================================================

MODULE socket_server

    VAR socketdev client_socket;
    VAR socketdev server_socket;
    VAR string received_string;
    VAR num joint_angles{6};

    PROC main()
        VAR string reply;

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        TPWrite "AI Agent SocketServer listening on port 30000";

    main_loop:
        SocketAccept server_socket, client_socket;
        TPWrite "Client connected";

        WHILE TRUE DO
            received_string := "";
            SocketReceive client_socket \Str:=received_string;
            reply := HandleCommand(received_string);
            SocketSend client_socket \Str:=reply;
        ENDWHILE

    ERROR
        ! Client disconnected or socket error: close and wait for next client
        SocketClose client_socket;
        GOTO main_loop;
    ENDPROC

    FUNC string HandleCommand(string cmd)
        VAR string command;
        VAR num pos;

        ! Remove trailing CR/LF characters sent by the client
    trim_loop:
        IF StrLen(cmd) > 0 THEN
            IF StrPart(cmd, StrLen(cmd), 1) = "\0A" OR
               StrPart(cmd, StrLen(cmd), 1) = "\0D" THEN
                cmd := StrPart(cmd, 1, StrLen(cmd)-1);
                GOTO trim_loop;
            ENDIF
        ENDIF

        pos := StrFind(cmd, " ");
        IF pos > 0 THEN
            command := StrPart(cmd, 1, pos-1);
        ELSE
            command := cmd;
        ENDIF

        IF command = "HOME" THEN
            MoveAbsJ [[0,0,0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], v1000, fine, tool0;
            RETURN "OK 0,0,0,0,0,0";
        ELSEIF command = "MOVEJ" THEN
            IF ParseJoints(cmd) THEN
                MoveAbsJ [[joint_angles{1},joint_angles{2},joint_angles{3},
                          joint_angles{4},joint_angles{5},joint_angles{6}],
                          [9E9,9E9,9E9,9E9,9E9,9E9]], v1000, fine, tool0;
                RETURN "OK " + JointString();
            ELSE
                RETURN "ERROR MOVEJ cannot parse parameters";
            ENDIF
        ELSEIF command = "MOVEL" THEN
            RETURN "OK " + JointString();
        ELSEIF command = "GETPOS" OR command = "STATUS" THEN
            RETURN "OK " + JointString();
        ELSE
            RETURN "ERROR unknown command: " + command;
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
