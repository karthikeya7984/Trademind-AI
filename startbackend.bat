@echo off
cd /d "c:\Users\chkar\OneDrive\Desktop\intern project\college intern\trademind-ai\backend"
"c:\Users\chkar\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
