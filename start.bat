@echo off
set PATH=C:\Users\chkar\AppData\Local\Programs\Python\Python312;C:\Users\chkar\AppData\Local\Programs\Python\Python312\Scripts;C:\Program Files\nodejs;%PATH%

echo Starting TradeMind AI...

start "Backend" cmd /k "cd /d "%~dp0backend" && set PATH=C:\Users\chkar\AppData\Local\Programs\Python\Python312;C:\Users\chkar\AppData\Local\Programs\Python\Python312\Scripts;%PATH% && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

start "Frontend" cmd /k "cd /d "%~dp0frontend" && set PATH=C:\Program Files\nodejs;%PATH% && npm run dev"

echo.
echo =============================================
echo  LOCAL ACCESS
echo  Frontend : http://localhost:3000
echo  Backend  : http://localhost:8000/docs
echo.
echo  NETWORK ACCESS (other devices)
echo  Frontend : http://10.131.59.250:3000
echo  Backend  : http://10.131.59.250:8000/docs
echo.
echo  Admin Login
echo  Email    : ch.karthikeya868769@gmail.com
echo  Password : Admin@2024
echo =============================================
