' 后台启动 AI Robot Demo：ROS2 + Gazebo 仿真 + Streamlit GUI，隐藏运行。
' 双击本文件或通过快捷方式调用（wscript.exe）。
' 启动逻辑在 scripts/launcher_background_*.sh 中（setsid 保持后台进程）。

Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
wslPath = Replace(scriptDir, "\", "/")
wslPath = "/mnt/" & LCase(Left(wslPath, 1)) & Mid(wslPath, 3)

' 1) ROS2 + Gazebo 仿真系统（隐藏后台）
ws.Run "wsl.exe -d Ubuntu-22.04 -e bash " & wslPath & "/scripts/launcher_background_sim.sh", 0, False

' 2) Streamlit GUI（隐藏后台，与仿真并行启动，不固定等待）
ws.Run "wsl.exe -d Ubuntu-22.04 -e bash " & wslPath & "/scripts/launcher_background_gui.sh", 0, False

' 3) 动态等待 GUI 就绪（最长 120 秒，每 2 秒轮询一次），就绪后立即打开浏览器
For i = 1 To 60
    WScript.Sleep 2000
    If UrlReady("http://localhost:8501") Then Exit For
Next
ws.Run "http://localhost:8501", 1, False

Function UrlReady(url)
    On Error Resume Next
    Dim http
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.open "GET", url, False
    http.setTimeouts 3000, 3000, 3000, 3000
    http.send
    If Err.Number = 0 And http.status = 200 Then
        UrlReady = True
    Else
        UrlReady = False
    End If
    Set http = Nothing
End Function
