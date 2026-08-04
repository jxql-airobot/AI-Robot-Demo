MODULE socket_server

    VAR socketdev client_socket;
    VAR socketdev server_socket;
    VAR string received_string;
    VAR num joint_angles{6};
    VAR robtarget pose_target := [[0,0,0],[1,0,0,0],[0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]];
    VAR jointtarget current_jt;

    PROC socket_main()
        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        TPWrite "AI Robot SocketServer listening on port 30000";

        WHILE TRUE DO
            SocketAccept server_socket, client_socket;
            TPWrite "Client connected";
            HandleClient;
            CloseClient;
        ENDWHILE
    ERROR
        IF ERRNO = ERR_SOCK_TIMEOUT THEN
            RETRY;
        ENDIF
    ENDPROC

    PROC CloseClient()
        SocketClose client_socket;
    ERROR
        RETURN;
    ENDPROC

    PROC HandleClient()
        VAR string reply;

        WHILE TRUE DO
            received_string := "";
            SocketReceive client_socket \Str:=received_string;
            received_string := TrimLine(received_string);
            reply := HandleCommand(received_string);
            SocketSend client_socket \Str:=reply + "\0A";
        ENDWHILE

    ERROR
        TPWrite "Client disconnected, waiting for next client";
        RETURN;
    ENDPROC

    FUNC string TrimLine(string str)
        VAR num i;
        FOR i FROM 1 TO 4 DO
            IF StrLen(str) > 0 THEN
                IF StrPart(str, StrLen(str), 1) = "\0A" OR
                   StrPart(str, StrLen(str), 1) = "\0D" THEN
                    str := StrPart(str, 1, StrLen(str)-1);
                ENDIF
            ENDIF
        ENDFOR
        RETURN str;
    ENDFUNC

    FUNC string HandleCommand(string cmd)
        VAR string command;
        VAR num pos;

        pos := StrMatch(cmd, 1, " ");
        IF pos > 0 THEN
            command := StrPart(cmd, 1, pos-1);
        ELSE
            command := cmd;
        ENDIF

        IF command = "HOME" THEN
            joint_angles{1} := 0;
            joint_angles{2} := 0;
            joint_angles{3} := 0;
            joint_angles{4} := 0;
            joint_angles{5} := 0;
            joint_angles{6} := 0;
            MoveAbsJ [[0,0,0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], v1000, fine, tool0;
            RETURN "OK " + JointString();
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
            IF ParsePose(cmd) THEN
                MoveL pose_target, v1000, fine, tool0;
                RETURN "OK " + JointString();
            ELSE
                RETURN "ERROR MOVEL cannot parse parameters";
            ENDIF
        ELSEIF command = "GETPOS" OR command = "STATUS" THEN
            RETURN "OK " + JointString();
        ELSE
            RETURN "ERROR unknown command: " + command;
        ENDIF
    ERROR
        RETURN "ERROR RAPID error " + NumToStr(ERRNO,0);
    ENDFUNC

    FUNC bool ParseJoints(string cmd)
        VAR num pos;
        VAR num i;
        VAR string body;
        VAR bool ok;

        pos := StrMatch(cmd, 1, " ");
        IF pos <= 0 THEN
            RETURN FALSE;
        ENDIF
        body := StrPart(cmd, pos+1, StrLen(cmd)-pos);

        FOR i FROM 1 TO 6 DO
            IF StrLen(body) = 0 THEN
                RETURN FALSE;
            ENDIF
            pos := StrMatch(body, 1, ",");
            IF pos > 1 AND pos < StrLen(body) THEN
                ok := StrToVal(StrPart(body, 1, pos-1), joint_angles{i});
                body := StrPart(body, pos+1, StrLen(body)-pos);
            ELSE
                ok := StrToVal(body, joint_angles{i});
                body := "";
            ENDIF
            IF NOT ok THEN
                RETURN FALSE;
            ENDIF
        ENDFOR
        RETURN TRUE;
    ENDFUNC

    FUNC bool ParsePose(string cmd)
        VAR num pos;
        VAR num i;
        VAR string body;
        VAR bool ok;
        VAR num vals{6};

        pos := StrMatch(cmd, 1, " ");
        IF pos <= 0 THEN
            RETURN FALSE;
        ENDIF
        body := StrPart(cmd, pos+1, StrLen(cmd)-pos);

        FOR i FROM 1 TO 6 DO
            IF StrLen(body) = 0 THEN
                RETURN FALSE;
            ENDIF
            pos := StrMatch(body, 1, ",");
            IF pos > 1 AND pos < StrLen(body) THEN
                ok := StrToVal(StrPart(body, 1, pos-1), vals{i});
                body := StrPart(body, pos+1, StrLen(body)-pos);
            ELSE
                ok := StrToVal(body, vals{i});
                body := "";
            ENDIF
            IF NOT ok THEN
                RETURN FALSE;
            ENDIF
        ENDFOR

        pose_target.trans.x := vals{1};
        pose_target.trans.y := vals{2};
        pose_target.trans.z := vals{3};
        ! rx=roll(X) ry=pitch(Y) rz=yaw(Z), degrees; OrientZYX uses Z-Y-X order
        pose_target.rot := OrientZYX(vals{6}, vals{5}, vals{4});
        RETURN TRUE;
    ENDFUNC

    FUNC string JointString()
        VAR string s;
        ! CJointT() reads the actual measured joint angles (truth readback)
        current_jt := CJointT();
        s := NumToStr(current_jt.robax.rax_1,2) + "," +
             NumToStr(current_jt.robax.rax_2,2) + "," +
             NumToStr(current_jt.robax.rax_3,2) + "," +
             NumToStr(current_jt.robax.rax_4,2) + "," +
             NumToStr(current_jt.robax.rax_5,2) + "," +
             NumToStr(current_jt.robax.rax_6,2);
        RETURN s;
    ENDFUNC

ENDMODULE
