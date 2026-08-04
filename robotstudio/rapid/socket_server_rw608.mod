! Minimal SocketCreate test for RobotWare 6.08 / IRC5
! Requires controller option 616-1 PC Interface

MODULE socket_server_rw608

    VAR socketdev server_socket;

    PROC socket_main()
        SocketCreate server_socket;
        TPWrite "SocketCreate OK";
    ENDPROC

ENDMODULE
