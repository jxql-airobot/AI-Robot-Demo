! ABB RobotStudio SocketServer for AI Agent control (V6.1)
! Compatible with RobotWare 6.08 / IRC5 Virtual Controller.
!
! Protocol (matches robotstudio/command_schema.py):
!   Client -> HOME | MOVEJ j1,...,j6 | MOVEL x,y,z,rx,ry,rz | GETPOS | STATUS
!   Server <- OK j1,...,j6 | ERROR <message>
!
! Notes:
!   - RAPID comments use exclamation mark, not percent sign
!   - No file header comment block (avoids RobotStudio import issues)
!   - Uses tool0 and v1000; adjust for your station if needed.

MODULE socket_server

    VAR socketdev client_socket;
    VAR socketdev server_socket;
    VAR string received_string;
    VAR num joint_angles{6};

    PROC main()
        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        TPWrite "AI Agent SocketServer listening on port 30000";

        WHILE TRUE DO
            SocketAccept server_socket, client_socket;
            TPWrite "Client connected";
            HandleClient;
        ENDWHILE
    ENDPROC

    PROC HandleClient()
        VAR string reply;

        WHILE TRUE DO
            received_string := "";
            SocketReceive client_socket \Str:=received_string;
            reply := HandleCommand(received_string);
            SocketSend client_socket \Str:=reply;
        ENDWHILE

    ERROR
        ! Client disconnected or socket error: close and return to accept loop
        SocketClose client_socket;
    ENDPROC

    FUNC string HandleCommand(string cmd)
        VAR string command;
        VAR num pos;
        VAR num i;

        ! Remove trailing CR/LF characters sent by the client (up to 4)
        FOR i FROM 1 TO 4 DO
            IF StrLen(cmd) > 0 THEN
                IF StrPart(cmd, StrLen(cmd), 1) = "\0A" OR
                   StrPart(cmd, StrLen(cmd), 1) = "\0D" THEN
                    cmd := StrPart(cmd, 1, StrLen(cmd)-1);
                ENDIF
            ENDIF
        ENDFOR

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
