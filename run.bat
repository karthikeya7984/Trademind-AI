@echo off
set PYTHON=C:\Users\chkar\AppData\Local\Programs\Python\Python312\python.exe
set ROOT=%~dp0

echo Checking uvicorn...
%PYTHON% -m uvicorn --version
if errorlevel 1 (
    echo Installing backend dependencies...
    %PYTHON% -m pip install -r "%ROOT%backend\requirements.txt"
)

echo Starting Backend...
start "TradeMind Backend" cmd /k "cd /d "%ROOT%backend" && C:\Users\chkar\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Frontend...
start "TradeMind Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo ==========================================
echo  Frontend  : http://localhost:3000
echo  Backend   : http://localhost:8000
echo  API Docs  : http://localhost:8000/docs
echo ==========================================
