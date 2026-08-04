MODULE test_clean_rw608

    VAR socketdev server_socket;
    VAR socketdev client_socket;
    VAR string received_string;

    PROC test_run()

        TPWrite "ABB RW608 TEST OK";

    ENDPROC

    PROC socket_create_test()

        SocketCreate server_socket;
        TPWrite "SocketCreate OK";

    ENDPROC

    PROC socket_bind_test()

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        TPWrite "SocketBind OK";

    ENDPROC

    PROC socket_listen_test()

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        TPWrite "SocketListen OK";

    ENDPROC

    PROC socket_accept_test()

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        SocketAccept server_socket, client_socket;
        TPWrite "SocketAccept OK";

    ENDPROC

    PROC socket_receive_test()

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        SocketAccept server_socket, client_socket;
        SocketReceive client_socket \Str:=received_string;
        TPWrite "Received: " + received_string;

    ENDPROC

    PROC socket_send_test()

        SocketCreate server_socket;
        SocketBind server_socket, "0.0.0.0", 30000;
        SocketListen server_socket;
        SocketAccept server_socket, client_socket;
        SocketReceive client_socket \Str:=received_string;
        SocketSend client_socket \Str:="SERVER ECHO: " + received_string;
        TPWrite "SocketSend OK";

    ENDPROC

ENDMODULE
