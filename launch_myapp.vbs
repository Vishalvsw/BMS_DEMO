Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\Users\kiran\Desktop\BMS_Application\start_myapp.bat" & Chr(34), 0
WScript.Sleep 3000
WshShell.Run "http://myapp.local:5000"
Set WshShell = Nothing
