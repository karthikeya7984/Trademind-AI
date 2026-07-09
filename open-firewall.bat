@echo off
echo Opening firewall ports for TradeMind AI...
netsh advfirewall firewall delete rule name="TradeMind Backend 8000" >nul 2>&1
netsh advfirewall firewall delete rule name="TradeMind Frontend 3000" >nul 2>&1
netsh advfirewall firewall add rule name="TradeMind Backend 8000" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="TradeMind Frontend 3000" dir=in action=allow protocol=TCP localport=3000
echo.
echo Done! Ports 8000 and 3000 are now open.
echo.
echo Access TradeMind AI from any device on your network:
echo   Frontend : http://10.131.59.250:3000
echo   API Docs : http://10.131.59.250:8000/docs
echo.
pause
