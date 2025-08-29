@echo off
cd /d "C:\Users\kiran\Desktop\BMS_Application\start_myapp.bat"
start /min python app.py
timeout /t 2 /nobreak >nul
exit
