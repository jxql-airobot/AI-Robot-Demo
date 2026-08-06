MODULE socket_server

    VAR socketdev client_socket;
    VAR socketdev server_socket;
    VAR string received_string;
    VAR num joint_angles{6};
    VAR string move_reply;
    ! 最近一次机器人错误（供 ERRINFO 查询），0/none 表示无错误
    VAR num last_errno := 0;
    VAR string last_err_name := "none";
    VAR robtarget pose_target := [[0,0,0],[1,0,0,0],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]];
    VAR jointtarget current_jt;

    PROC socket_main()
        ! let MoveL auto-pick the closest valid axis configuration and handle wrist singularity
        ConfL \Off;
        SingArea \Wrist;
        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        TPWrite "AI Robot SocketServer listening on port 30000";

        WHILE TRUE DO
            ! WAIT_MAX: wait forever for clients. The default 60s timeout
            ! raised 41581 -> RETRY -> exceeded NoOfRetry (default 4) after
            ! ~5 idle minutes -> 40195 limit error -> program stopped.
            SocketAccept server_socket, client_socket \Time:=WAIT_MAX;
            TPWrite "Client connected";
            HandleClient;
            CloseClient;
        ENDWHILE
    ERROR
        IF ERRNO = ERR_SOCK_TIMEOUT THEN
            RETRY;
        ENDIF
        ! any other accept/session error: clean up the client socket and
        ! keep the server listening instead of leaving a stale CLOSE_WAIT
        CloseClient;
        RETRY;
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
        TPWrite "Client disconnected, closing client socket";
        CloseClient;
        RETURN;
    ENDPROC

    ! 结构化运动错误回复：ERROR_RAPID <errno> <code>
    ! 让 Python 侧能识别真实机器人执行错误（如 50050 位置超出范围），
    ! 并保持 SocketServer 继续监听，不因单次运动错误退出。
    FUNC string ErrorCodeName(num errno)
        IF errno = 50050 THEN
            RETURN "position_unreachable";
        ELSEIF errno = 50027 THEN
            RETURN "joint_out_of_range";
        ELSEIF errno = 50501 THEN
            RETURN "short_distance";
        ELSEIF errno = 41595 THEN
            RETURN "socket_error";
        ELSEIF errno = 10020 THEN
            RETURN "execution_error_state";
        ELSEIF errno = 40195 THEN
            RETURN "limit_error";
        ELSE
            RETURN "motion_execution_error";
        ENDIF
    ENDFUNC

    FUNC string MotionErrorReply(num errno)
        last_errno := errno;
        last_err_name := ErrorCodeName(errno);
        RETURN "ERROR_RAPID " + NumToStr(errno,0) + " " + last_err_name;
    ENDFUNC

    ! 查询最近一次机器人错误：ERRINFO <errno> <name>（0 none 表示无错误）
    FUNC string ErrorInfoReply()
        RETURN "ERRINFO " + NumToStr(last_errno,0) + " " + last_err_name;
    ENDFUNC

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
                DoMoveL;
                RETURN move_reply;
            ELSE
                RETURN "ERROR MOVEL cannot parse parameters";
            ENDIF
        ELSEIF command = "GETPOSE" THEN
            RETURN "OK " + PoseString();
        ELSEIF command = "GETPOS" OR command = "STATUS" THEN
            RETURN "OK " + JointString();
        ELSEIF command = "ERRINFO" THEN
            RETURN ErrorInfoReply();
        ELSE
            RETURN "ERROR unknown command: " + command;
        ENDIF
    ERROR
        RETURN MotionErrorReply(ERRNO);
    ENDFUNC

    PROC DoMoveL()
        MoveL pose_target, v1000, fine, tool0;
        move_reply := "OK " + JointString();
        RETURN;
    ERROR
        move_reply := MotionErrorReply(ERRNO);
        RETURN;
    ENDPROC

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

        ! rx=roll(X) ry=pitch(Y) rz=yaw(Z), degrees; OrientZYX uses Z-Y-X order
        IF vals{4} = 0 AND vals{5} = 0 AND vals{6} = 0 THEN
            ! all-zero orientation: keep current tool orientation (CRobT),
            ! avoid wrist singularity on pure position moves
            pose_target := CRobT();
            ! protocol uses meters, RAPID robtarget.trans uses millimeters
            pose_target.trans.x := vals{1} * 1000;
            pose_target.trans.y := vals{2} * 1000;
            pose_target.trans.z := vals{3} * 1000;
        ELSE
            pose_target.trans.x := vals{1} * 1000;
            pose_target.trans.y := vals{2} * 1000;
            pose_target.trans.z := vals{3} * 1000;
            pose_target.rot := OrientZYX(vals{6}, vals{5}, vals{4});
        ENDIF
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

    FUNC string PoseString()
        VAR robtarget p;
        VAR string s;
        p := CRobT();
        ! report in meters to match the MOVEL protocol
        s := NumToStr(p.trans.x/1000,4) + "," +
             NumToStr(p.trans.y/1000,4) + "," +
             NumToStr(p.trans.z/1000,4) + "," +
             NumToStr(EulerZYX(\X, p.rot),2) + "," +
             NumToStr(EulerZYX(\Y, p.rot),2) + "," +
             NumToStr(EulerZYX(\Z, p.rot),2);
        RETURN s;
    ENDFUNC

ENDMODULE
